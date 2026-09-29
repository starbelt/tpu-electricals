# `sb-tpu` — Open Issues

Review of the `sb-tpu` design against the Google **Coral Dev Board Micro** reference
(both the original Altium project and the KiCad conversion under `../coral-micro/`).

| | |
|---|---|
| Design reviewed | `kicad/sb-tpu.kicad_sch` / `kicad/sb-tpu.kicad_pcb` at commit `6978607` |
| Reference | `Coral Dev Board Micro` — Altium `.SchDoc` / `.PcbDoc` plus the KiCad conversion |
| Method | Netlists exported with `kicad-cli sch export netlist` and diffed programmatically: RT1176 ball-by-ball, Coral-module pin-by-pin, plus PCB geometry (track lengths, widths, layers, pad-to-pad distances, copper zones) parsed out of `sb-tpu.kicad_pcb` |
| Scope | Documentation only. **No design files were modified.** |

Coral fits and omits parts through the Altium `DNP` variant field, so a resistor existing in
the Coral schematic does not mean it is on the board. Every Coral comparison below uses the
**fitted** population, not the drawn one.

## Field notes from bring-up

Observations from the bench, recorded here because they confirm or reframe several findings:

* **The watchdog was removed, and the board then powered on.** This confirms item 1 as an
  actual, not theoretical, blocker.
* **USB power-on sequencing did not work**, so the board was reverted to being powered purely
  from the **3V3 rail**, which **does** work. See the dedicated analysis in
  "Why the board boots from the 3V3 rail but not from USB-C 5V" below.
* **With rail-only power, `D17` (`USB1_VBUS`) sits at 0 V**, because it is tied only to
  `VUSB`. The USB PHY therefore never sees a valid session and will not enable without
  bodging `D17` to external power. This is discussed under item 5 — the pin itself is wired
  the same way Coral wires it, so the question is why `VBUS` never arrives, not whether `D17`
  should be tied elsewhere.

## Severity key

| Tag | Meaning |
|---|---|
| **BLOCKER** | Board cannot work as built; fix before anything else |
| **DEFECT** | Real divergence from the reference with a functional consequence |
| **RISK** | Works today but outside good practice or margin, or unverified |
| **CLEARED** | Suspected, investigated, found correct — no action needed |

## Summary

| # | Issue | Area | Severity |
|---|---|---|---|
| 1 | Watchdog `U5` re-asserts `POR_B` every ~250 ms, forever | Power / reset | **BLOCKER** |
| 2 | TPU module `PCIE_TX_N/P` (pins 4, 5) shorted to GND | TPU | **BLOCKER** |
| 3 | `VSYS_3V3` is a one-node net → `IC7` `VCCB` unpowered | USB-C | **BLOCKER** |
| 4 | Boot-UART isolation switch (Coral `U14`) never implemented | Boot | **DEFECT** |
| 5 | `DA_nONKEY` has no pull-up (Coral `R166` missing) | Buttons | **DEFECT** |
| 6 | `POR_B` has no filter cap (Coral `C115` missing) on an 87 mm net | Reset | **DEFECT** |
| 7 | TPU bulk caps 21 mm from `VIN`; no power planes anywhere | Layout / power | **DEFECT** |
| 8 | USB2 pair skew 2.33 mm; USB1 pair has asymmetric vias | Layout / USB | **RISK** |
| 9 | `MCM_3V3` routed as a 0.15–0.2 mm trace, 6 vias, no plane | Layout / power | **RISK** |
| 10 | Floating MCU pins (`ONOFF`, `WAKEUP`, boot UART, …) | MCU | **RISK** |
| 11 | `I2C5_SDA` assigned to the `90ohmdiff` net class | Layout | **RISK** |
| 12 | `SKRPADE010` terminal pairing unverified against the drawing | Buttons | **RISK** |
| 13 | Duplicate / incorrect pin names in the RT1176 symbol | Library | **RISK** |
| 14 | Non-sealed tact switches; vendor excludes space use | Mechanical | **RISK** |
| 15 | SDRAM bus length spread of ~19.5 mm across four layers | Layout / SDRAM | **DEFECT** |
| 16 | 11 of 65 3D-model paths point at missing files | Library hygiene | **RISK** |
| 17 | `IC1` `EN2` tied to `VSYS`, so Buck 2 never arms soft-start | Power / USB boot | **DEFECT** *(downgraded)* |
| 18 | `IC1` `SDA` / `SCL` left floating against datasheet instruction | Power | **DEFECT** |
| 19 | On USB, all 3.3 V current must pass Buck 2 (600 mA rated) — fails at TPU enable | Power / TPU | **DEFECT** |
| 20 | On rail power Buck 2 runs in dropout; `nPOR2` can assert `POR_B` | Power / reset | **DEFECT** |
| 21 | `MCU_DCDC_IN` caps `C45`/`C46`/`C48` return to a floating net, not `GND` | Power / USB boot | **BLOCKER (USB)** |

---

# Blockers

## 1. BLOCKER — Watchdog `U5` holds the board in a ~250 ms reset loop

**Confirmed on the bench: `U5` was removed and the board then powered on.**

`U5` is a **TPS3813K33DBVR** window watchdog and supervisor. As wired:

| Pin | Name | Net |
|---|---|---|
| 1 | `WDI` | `VDD_3V3` — **tied static high** |
| 2 | `GND` | `GND` |
| 3 | `WDT` | `GND` |
| 4 | `VDD` | `VDD_3V3` |
| 5 | `WDR` | `VDD_3V3` |
| 6 | `RESET` (open-drain) | `POR_B` |

From the TI datasheet (SLVS331J):

* `WDI` — *"Watchdog timer input. This input must be driven at all times and not left
  floating."* The watchdog is triggered by **edges** on `WDI`. There is no disable pin.
* `WDT = 0 V` → watchdog upper time-out **0.2 / 0.25 / 0.3 s** (min / typ / max).
* `WDR = VDD` with `WDT = 0 V` → window ratio **1:124.9**, so the lower boundary is ≈ 2 ms.
* Power-on reset delay `td` = 25 ms typical.

`WDI` is hard-wired to `VDD_3V3`, so it never produces a trigger edge. The sequence is:

1. `VDD_3V3` rises past `V_IT` (2.93 V for the K33 option) → `RESET` released after 25 ms.
2. The first watchdog window opens, with no lower boundary.
3. No trigger arrives within 250 ms → `RESET` asserts, pulling `POR_B` low.
4. Repeat, indefinitely.

**Consequence:** the MCU is reset roughly four times per second and can never finish
booting. Every downstream symptom — USB not enumerating, the TPU never coming up, boot
appearing "unstrapped" — is consistent with this, and should be re-tested only after it is
cleared.

**Options**

* **Depopulate `U5`** (fastest). `POR_B` keeps its 10 kΩ pull-up (`R1` to `VDD_SNVS_ANA`)
  and the `SW1` and `IC1` `nPOR` paths. The schematic already labels it *"Optional Watchdog
  Timer"* — but as wired it is not optional.
* **Or** route `WDI` to a spare MCU GPIO that firmware toggles every 2–250 ms, and only
  populate `U5` once that firmware exists. `WDT = VDD` would widen the window to 2.5 s.

`RESET` is **open-drain**, so there is no driver contention with `SW1` or with `IC1`'s
`nPOR1` / `nPOR2` — that part of the circuit is fine.

The Coral reference has no equivalent part; reset supervision there lives inside the DA9061
PMIC that was removed in this design.

## 2. BLOCKER — Coral module `PCIE_TX_N/P` (pins 4, 5) are shorted to GND

`IC2` is the Coral accelerator module (`G313-06329-00` — the same die and package as Coral's
`U23` / `LBPB0ZZ1WV`). The PCIe pins are handled differently on the two boards:

| Module pin | Function | Direction | Coral (`U23`) | sb-tpu (`IC2`) |
|---|---|---|---|---|
| 4 | `PCIE_TX_N` | **output** | **no-connect** | **GND** |
| 5 | `PCIE_TX_P` | **output** | **no-connect** | **GND** |
| 7 | `PCIE_RX_P` | input | GND | GND |
| 8 | `PCIE_RX_N` | input | GND | GND |
| 10 | `PCIE_REFCLK_N` | input | GND | GND |
| 11 | `PCIE_REFCLK_P` | input | GND | GND |

Grounding the unused **inputs** (7, 8, 10, 11) matches Coral. Grounding the **transmitter
outputs** (4, 5) does not — Coral explicitly leaves them floating and marks them no-connect
in its netlist.

**Consequence:** if the module's PCIe SerDes transmitter is ever enabled — including
transiently during its own power-up or self-test, before `USB_SEL` is sampled — it is
driving a differential output pair into a dead short. Best case that means elevated current
and heat during init; worst case, permanent damage to the module's output stage. There is
no upside, because the pins are unused either way.

**Fix:** lift pins 4 and 5 to no-connect, matching Coral. On the existing hardware, freeing
those two pads under a QFN-120 is not practical, so treat this as a respin item — and in the
meantime keep it in mind as a candidate explanation for any unexplained module current draw.

*Evidence: `IC2.4` and `IC2.5` appear in the `GND` net of the exported sb-tpu netlist, while
`U23` pins 4 and 5 appear as `unconnected-(U23-PCIE_USB3_TX_N-Pad4)` and `-Pad5` in Coral's.*

## 3. BLOCKER — `VSYS_3V3` is a dangling net, so the USB-C level translator is unpowered

`IC7` (**SN74AUP1T34QDCKRQ1**, 1-bit A→B level translator) sits between the MCU's
`USB_PORT_RT` GPIO and the `PORT` pin of `IC8` (**PTN5150A** USB-C CC controller):

```
U4.R15 (GPIO_AD_08) ── USB_PORT_RT ── IC7.2 (A)     IC7.4 (B) ── IC8.3 (PORT)
                                      IC7.1 VCCA = VDD_1V8
                                      IC7.5 VCCB = VSYS_3V3   <-- ONE-NODE NET
```

`VSYS_3V3` appears exactly once in the entire design — on `IC7` pin 5. **There is no source
for it.** `VCCB` floats, so the B-side output cannot drive, and the PTN5150's `PORT` input
(which selects UFP / DFP / DRP role) is left undefined.

This lines up with two of the designer's own notes on the IO sheet: *"AON Domain Not
Present"* and *"Do I need this level shifter?"* The root cause is structural. Coral has
**two** 1.8 V domains, `VDD_1V8` and `VDD_1V8_AON`, plus an always-on 3.3 V. When the PMIC
was removed the AON domain went with it, and its dependents were never re-homed. Coral
powers the equivalent translator's output side from `VUSB` (`U4.6 VCCO → VUSB`, Coral
sheet 13).

**Fix, pick one:**

* Tie `IC7.5 VCCB` to `VUSB` — the same rail as `IC8.12 VDD` and `IC8.4 VBUS_DET`, and what
  Coral does. This is the direct fix.
* Or delete `IC7` entirely and strap `IC8.PORT` to the fixed role the board needs (`sb-tpu`
  is always a USB device / UFP on `J1`), freeing `GPIO_AD_08`.

**Bodge for the current board:** a wire from `IC7` pin 5 to `IC8` pin 12.

---

# Why the board boots from the 3V3 rail but not from USB-C 5V

*Re-evaluated 2026-09-28 against the working-tree schematic, the LM3370 datasheet (SNVS406N)
and the bring-up captures. The earlier version of this section ranked four power
contributors. Two are now closed and the other two narrow considerably. The re-check also
turned up a new defect (item 21) that fits the USB-only symptom better than any of them.*

The two supply paths are **not symmetric**:

| | From `+3V3` rail | From USB-C 5 V |
|---|---|---|
| `VSYS` | `+3V3` → `U2` INB → ~3.25 V | `VUSB` → `D2` → `VSYS_5V` → `U2` INA → ~4.65 V |
| `VDD_SNVS_IN` | `+3V3` → **`D3` Schottky** → `VLDO_3V3` | `VSYS_5V` → **`U3` LDO** → `D4` → `VLDO_3V3` |
| **`VDD_3V3`** | **`+3V3` → `U1` INB, direct from the bus.** Buck 2 is bypassed. | **Buck 2 only.** `IC1` ch2 → `VDD_3V3_SENSE` → `U1` INA |
| `MCU_DCDC_IN` | stiff bus supply through `U1` and `R34` | a 2 MHz buck through `U1` and `R34`, **with no local capacitance** (item 21) |
| Buck 2 switching | 100 % duty (dropout), not switching | switching, PFM at light load |

On rail power, the 3.3 V domain never depends on Buck 2. On USB it does, entirely.

## Closed

* **DCDC_IN ramp rule (was contributor 2).** `R38`/`C55` match the Coral reference, and the
  ramp was validated on the logic analyzer (`bringup/dcdc_pswitch_*.sal`). The arithmetic
  below also shows that Buck 2's worst-case hard start finishes in well under the 2.0 ms
  limit.
* **CC role / unstable VBUS (was item 3).** Fixed in `63e516a`: `PORT` is now tied low, so the
  PTN5150A comes up as a UFP instead of DRP. `D17` follows `VUSB` as intended.

## Contributor 1 — Buck 2 soft-start (item 17): real non-compliance, unlikely root cause

The datasheet fact still holds: *"Soft start is activated only if EN goes from logic low to
logic high after VIN reaches 2.7V,"* and `EN2` is still tied to `VSYS`. So Buck 2 starts
without soft-start. Its consequences were overstated before:

* **No foldback, no latch.** The datasheet describes the limit as *"cycle-by-cycle current
  limiting using an internal comparator that trips at 1200 mA (typ.)"*. The only other mode
  is a timed limit for a shorted output. So a hard start charges the output at roughly
  0.85–1.4 A and then regulates. There is no restart loop.
* **The load capacitance is about half the earlier estimate.** The previous figure of ~50 µF
  counted `C45` 22 µF and `C48` 4.7 µF, but those are not connected to `GND` (item 21).
  What Buck 2 actually sees is `C9` 10 µF, `C3` 4.7 µF, `C49` 4.7 µF plus small ADC and USB
  caps: **about 20–25 µF nominal**, less after DC-bias derating.
* **Charge time:** 25 µF × 3.3 V / 0.85 A ≈ **0.1 ms**. This is too short to pull `VSYS` down
  meaningfully, given 18.8 µF on `VSYS` and a USB host's ≥ 120 µF behind the cable. It is also
  more than an order of magnitude inside the 2.0 ms `DCDC_IN` limit.

**Verdict:** fix it on the respin, because it's one resistor and one capacitor and the
datasheet requires it. But on its own it does not explain a board that won't start from USB.
**Retire the "lift `EN2`" bodge as the first experiment.**

## Contributor 3 — Buck 2 current headroom (item 19): real, but it can't stop boot

Buck 2 is rated **600 mA continuous** (850 mA minimum peak switch limit). The key fact is
that `TPU_POW_EN` has a 4.7 kΩ pull-down (`R31`), so **`U8` is off until firmware enables
the TPU**, and SDRAM is on Buck 1 (`VDD_1V8`). During boot, Buck 2 carries only the RT1176's
3.3 V domains and `DCDC_IN`, well inside 600 mA.

So item 19 is **a failure at TPU enable, not at boot**. The expected signature is a board
that boots and enumerates on USB, then resets or drops the TPU when `TPU_POW_EN` asserts or
on the first inference burst. The Edge TPU alone is on the order of 2 W at full rate
(4 TOPS at 2 TOPS/W), about 0.6 A at 3.3 V. Together with the MCU, that exceeds one
LM3370 channel. It is a sizing decision for the respin: either a larger 3.3 V converter or
a documented rule that the TPU needs rail power.

**Worth separating on the bench:** if "does not work on USB" means *never boots*, look at
item 21 before item 19. If it means *boots, then falls over when the TPU starts*, it is
item 19. It may also be item 20 (`nPOR2` on a sagging Buck 2 output asserting `POR_B`).

## New leading suspect — `MCU_DCDC_IN` has no decoupling to ground (item 21)

`C45` (22 µF), `C46` (0.1 µF) and `C48` (4.7 µF) each have one pad on `MCU_DCDC_IN`. Their
other pads connect **only to each other**, on `Net-(C45-Pad2)`, and not to `GND`. This is
the same in the schematic and in `sb-tpu.kicad_pcb`. The RT1176's internal DCDC, a switching
converter drawing pulsed input current, has **no input capacitor at its pins**. The nearest
real capacitance is `C3` 4.7 µF on `VDD_3V3`, behind `R34`, the trace and `U1`.

This fits the asymmetry exactly:

* **Rail power:** `+3V3` from the satellite bus is a low-impedance source with its own bulk,
  and it comes through `U1` channel B. It can absorb the DCDC's switching and load-step
  current even without local caps.
* **USB power:** the source is Buck 2, which idles in PFM at light load with 0.8–1.6 %
  ripple bands. When `DCDC_PSWITCH` enables the internal DCDC, the step has to come through
  an ideal-diode OR and 0.1 Ω into ~15 µF of distant capacitance, while Buck 2 moves from
  PFM to PWM. A dip on `DCDC_IN` can brown out the internal DCDC. A dip on
  `VDD_3V3_SENSE` below 85 % (2.8 V) trips `nPOR2`, which holds `POR_B` low for about 50 ms,
  and the cycle repeats.

**Bodge:** wire the shared `C45`/`C46`/`C48` node to the nearest `GND` via. Then repeat the
USB power-up. This is the first experiment to run.

## Minor — SNVS vs `DCDC_IN` ordering on USB

On USB, `VDD_SNVS_IN` waits for `U3`'s LDO, which races the `U2` → Buck 2 → `U1` path. The
LDO should win, but capture it once alongside the item 21 retest. `TPU_power_phasing.py`
already checks it.

## Suggested bench sequence

1. **Ground the `C45`/`C46`/`C48` common node** (item 21). Retry USB-C power-up.
2. With a Saleae or scope, capture `MCU_DCDC_IN`, `VDD_3V3_SENSE` (`TP2`), `POR_B` and
   `DCDC_PSWITCH` over the first ~100 ms of a USB power-up. A `DCDC_IN` or `TP2` dip that lines
   up with `DCDC_PSWITCH` rising and is followed by a 50 ms `POR_B` low confirms item 21 or 20.
   Also run `TPU_power_phasing.py` on the same capture for the SNVS ordering.
3. Once it boots on USB, **assert `TPU_POW_EN`** while watching `VDD_3V3_SENSE` and `POR_B`.
   A collapse here is item 19, which needs a respin decision, not a bodge.
4. Only if 1–3 are clean and USB start-up still fails: add the `EN2` RC (item 17) as the
   last power-side experiment.

---

# Defects

## 4. DEFECT — Boot-UART isolation switch was never implemented

`kicad/RT1176_2.kicad_sch` carries the note:

> *"Prevent UART from being driven at boot so that USB boot mode may be reached. Drive
> `BT_CFG_IO_EN` to enable pins"*

…and a graphic labelled *"BOOT ISLOATION SWITCH"* — but **`BT_CFG_IO_EN` does not exist as a
net**, and no isolation switch was placed. The string appears only as schematic text.

Coral implements this with a second bilateral switch:

| Coral | sb-tpu |
|---|---|
| `U14` = **74LVC2G66GT** (XSON8) | *absent* |
| `U14.1 1Y` → `LPUART1_TXD` (console side) | — |
| `U14.2 1Z` → `LPUART1_TXD_BT` (MCU ball L13) | `U4.L13` — **floating** |
| `U14.5 2Y` → `LPUART1_RXD` | — |
| `U14.6 2Z` → `LPUART1_RXD_BT` (MCU ball M15) | `U4.M15` — **floating** |
| `U14.3 / .7` (`2E` / `1E`) → `/BT_CFG_IO_EN` | — |
| `R53` 100 kΩ, `LPUART1_TXD_BT` → `VDD_1V8` | *absent* |
| `R21` 100 kΩ, `LPUART1_RXD_BT` → `VDD_1V8` | *absent* |

**Consequence:** the RT1176 boot ROM's serial downloader polls both USB and LPUART1. With
`LPUART1_RXD_BT` floating and no 100 kΩ pull-up, the ROM can see spurious activity on the
UART and latch onto UART download instead of USB. That matches the IO-sheet note *"UART
Console Not Available During Boot. Attempts to connect via UART during boot may interrupt
boot seq."* and, most likely, the README's *"NXP boot pin is unstrapped; requires jumper
wiring for a proper boot sequence."*

**Minimum fix:** add the two 100 kΩ pull-ups from `LPUART1_TXD_BT` and `LPUART1_RXD_BT` to
`VDD_1V8`. **Full fix:** add the `74LVC2G66` isolation switch and a `BT_CFG_IO_EN` GPIO, as
Coral does. The part is already in the BOM — `IC5` is the same `74LVC2G66GT,115`.

> **Note:** the *boot-mode straps themselves are correct* — see Cleared item **C1**. The
> README line about an unstrapped boot pin is not supported by the netlist and should be
> reworded to point at this UART issue instead.

## 5. DEFECT — `DA_nONKEY` has no pull-up, so the buttons' idle level is undefined

The user-button / boot-mode network is copied from Coral's sheet 16 and matches it
component-for-component and value-for-value — **except for one missing resistor**.

| Function | Coral (fitted) | sb-tpu | Match |
|---|---|---|---|
| `BOOT_MODE1` pull-up | `R29` 4.7 kΩ → `VDD_1V8` | `R51` 4.7 kΩ → `VDD_1V8` | yes |
| `BOOT_MODE0` pull-up | `R30` 4.7 kΩ → `VDD_1V8` | `R52` 4.7 kΩ → `VDD_1V8` | yes |
| `BOOT_MODE0` pull-down FET | `Q4` DMN3900 + `R31` 100 Ω | `Q2` DMN3900 + `R53` 100 Ω | yes |
| Button → `BOOT_MODE1` | `D6` Schottky, A = `BOOT_MODE1`, K = `DA_nONKEY` | `D8`, same orientation | yes |
| Button → `USER_BUTTON` | `D1` Schottky, A = `USER_BUTTON`, K = `DA_nONKEY` | `D7`, same orientation | yes |
| `USER_BUTTON` pull-up | `R167` 100 kΩ → `VDD_SNVS_ANA` | `R50` 100 kΩ → `VDD_SNVS_ANA` | yes |
| **`DA_nONKEY` pull-up** | **`R166` 100 kΩ → `VDD_1V8_AON`** | **none** | **NO** |

On Coral, `R166` clamps `DA_nONKEY` to about 2.3 V — the divider formed by `R167` (100 kΩ
from ~3.0 V, through `D1`) against `R166` (100 kΩ to 1.8 V). On `sb-tpu` the node has **no DC
path to any rail**: both Schottky cathodes point *into* it, and the only other connection is
the switch. Its idle voltage is therefore set purely by diode reverse leakage, which is
part-, temperature- and humidity-dependent.

**Consequence:** the button still reads correctly at room temperature — pressing it pulls
`USER_BUTTON` and `BOOT_MODE1` down to a Schottky drop, comfortably below `V_IL`. But the
released state is a high-impedance node with roughly 40 pF of diode and track capacitance
and no restoring current. That is an EMI, ESD and — for a picosatellite — single-event-
transient susceptibility: a disturbance that momentarily forward-biases `D8` pulls
`BOOT_MODE1` low and, on the next reset, drops the part into serial-downloader mode.

**Fix:** add a 100 kΩ pull-up from `DA_nONKEY` to `VDD_1V8`. (`VDD_1V8_AON` does not exist
here; `VDD_1V8` is the right substitute, because it also keeps `DA_nONKEY` from exceeding
`NVCC_LPSR`, the domain `BOOT_MODE1` lives in.)

### On "D17 on the MCU may need to be low or floating"

**Ball D17 on the RT1176 is `USB1_VBUS`** — not a boot or button pin. Its wiring is:

```
J1 (USB-C) VBUS ── VUSB ──+── U4.D17  (USB1_VBUS)
                          +── IC8.12  (PTN5150 VDD)
                          +── IC8.4   (PTN5150 VBUS_DET)
                          +── D2.A → VSYS_5V   (board power path)
```

Coral wires `U5.D17` to `VUSB` in exactly the same way, with `C252` local. **This is not a
divergence from the reference**, and it is not a wiring error.

The bring-up observation is nevertheless real: **with the board powered from the 3V3 rail,
`VUSB` is 0 V, so `D17` is 0 V and the USB1 PHY never sees a valid session.** That is the
*intended* behaviour of a VBUS-sense pin — it is how the controller knows whether a host is
attached — so the question is not where `D17` should be tied, but **why VBUS never arrived**
when a host was connected. The leading answer is the CC role problem in item 3: with `PORT`
floating the PTN5150A is in DRP mode and a Type-C source may never settle on supplying VBUS.
Bodging `D17` to external power worked because it supplied by hand the VBUS-present
indication that the CC logic failed to obtain.

**Do not fix this by tying `D17` permanently to 3.3 V.** The device would then always believe
a host is attached, which breaks session detection, suspend/resume and the boot ROM's
downloader logic. Fix the CC role (item 3) and `D17` follows correctly. If a rail-powered,
USB-free configuration is genuinely wanted, gate the USB stack in firmware instead.

Two further points:

* **Supply ordering.** `VUSB` reaches `D17` the instant the cable is plugged, whereas
  `VDD_SNVS_IN` only comes up after `D2` plus the `U3` (TCR2LN33) LDO start-up. NXP's rule is
  that no I/O may be driven before its supply. Measure `VUSB` against `VLDO_3V3` at hot-plug;
  if the gap is more than a few hundred microseconds, add a small series resistor and clamp
  on the `D17` branch, or a `VUSB`-referenced RC so `D17` lags `VDD_SNVS_IN`. This matters
  more now that the board is normally rail-powered, because plugging USB into an
  already-running board drives `D17` with the rest of the chip fully up — the safer of the
  two orders — but unplugging leaves `VUSB` decaying through `IC8` and `D2`.
* **The actual button defect is item 5 above**, plus the unverified switch pinout in item 12.
  Both are far more likely to produce "buttons behave wrongly" than anything at `D17`.

## 6. DEFECT — `POR_B` has no filter capacitor

| | Coral | sb-tpu |
|---|---|---|
| Pull-up | `R215` 10 kΩ → `VDD_SNVS_ANA` | `R1` 10 kΩ → `VDD_SNVS_ANA` (matches) |
| **Filter** | **`C115` 0.1 µF → `GND`** | **none** |
| Reset button | `SW3`, direct to GND | `SW1`, direct to GND |

`POR_B` on this board is also unusually long and exposed: **86.8 mm of routing spread over
four layers with 3 vias**, fanning out to seven nodes — `U4.T10`, `IC1.nPOR1`, `IC1.nPOR2`,
`U5.RESET`, `SW1`, `R1`, and header pin `J5.15`, which leaves the board entirely.

With a 10 kΩ pull-up, no capacitor and an off-board stub, that is a large high-impedance
antenna on the one net that can reset the processor. Coral's `C115` gives a roughly 1 ms RC
that both debounces the switch and filters pickup.

**Fix:** add 0.1 µF from `POR_B` to `GND`, placed at the MCU's `T10` ball. Also consider a
series resistor into the `J5.15` header stub.

## 7. DEFECT — The TPU's bulk decoupling is 21 mm away, with no power plane

Measured pad-to-pad from `IC2`'s nearest `MCM_3V3` (`VIN`) ball:

| Cap | Value | Distance to nearest `IC2` VIN pad |
|---|---|---|
| `C34`–`C39` | 0.1 µF x6 | 2.19 – 2.40 mm |
| `C40` | 1 µF | **21.53 mm** |
| `C42` | 22 µF | **21.02 mm** |
| `C43` | 22 µF | **20.82 mm** |
| `C94` | 0.1 µF | **16.94 mm** |
| `C33` | 0.1 µF (`MCM_1V8`) | 4.33 mm |

The 22 µF bulk pair sits next to `U8` and `IC3` at the far side of the board, not at the
load. Coral clusters its fitted bulk (`C42` and `C91`, both 22 µF) within a few millimetres
of the module edge — 11.7 mm and 13.1 mm from the package **centre**, on a 10 x 15 mm package.

Compounding this: **the board has no power planes at all.** The only two copper zones in
`sb-tpu.kicad_pcb` are `GND` on `In1.Cu` and `GND` on `In4.Cu`. `In2.Cu` and `In3.Cu` are
declared as power and signal layers in the stackup but carry only routed traces. Every supply
rail — `VDD_3V3`, `VDD_1V8`, `MCM_3V3`, `VSYS` — is a 0.15–0.2 mm trace.

**Consequence:** the Edge TPU draws large, fast current steps. With about 21 mm of narrow
trace (on the order of 25–35 nH plus 100–200 mΩ) between it and any bulk capacitance, the
local rail will sag on inference bursts even though the DC operating point looks fine. This
is a strong candidate for intermittent or load-dependent TPU misbehaviour.

**Fix:** move at least one 22 µF — ideally both — to within a few millimetres of the `VIN`
pins, keep the six 0.1 µF where they are, and pour `MCM_3V3` as a zone on `In2.Cu` from
`U8`'s output to the module.

---

# Remaining issues

Severity is tagged per item.

## 8. RISK — USB differential-pair skew and inconsistent geometry

Measured from the PCB:

| Net | Length | Vias | Widths (mm) | Layers |
|---|---|---|---|---|
| `USB2_TPU_P` | 12.86 mm | 0 | 0.1554 | F.Cu |
| `USB2_TPU_N` | 15.19 mm | 0 | **0.15 + 0.1554** | F.Cu |
| `OTG1_D_P` | 2.59 mm | 0 | 0.1554 | F.Cu |
| `OTG1_D_N` | 3.84 mm | 0 | 0.1554 | F.Cu |
| `/IO/USB_DP_CON` | 7.34 mm | **1** | 0.15 + 0.2 | F.Cu + B.Cu |
| `/IO/USB_DN_CON` | 8.69 mm | **2** | 0.2 | F.Cu + B.Cu |

* **MCU ↔ TPU (`USB2_TPU_*`): 2.33 mm intra-pair mismatch**, about 13 ps. USB-IF board
  guidance is under 1.9 mm (75 mil). A marginal violation.
* **USB-C ↔ MCU:** total per leg is 9.93 mm (P) against 12.53 mm (N) — a **2.6 mm mismatch**
  — and the connector-side halves use **unequal via counts** (1 against 2) plus mixed
  0.15 / 0.2 mm widths. Asymmetric vias are a mode-conversion source, not just a length error.
* Pair spacing is inconsistent. `USB2_TPU` holds a 0.127 mm edge gap, matching the class, but
  `OTG1_D_*` drifts between roughly 0.21 and 0.34 mm.
* The `90ohmdiff` net class has `track_width` **0.0948 mm** but `diff_pair_width`
  **0.127 mm**, and the pairs are actually routed at **0.1554 mm**. Three different numbers,
  and neither class value was used.

**The impedance itself is fine.** At the routed 0.1554 mm width and 0.127 mm gap on F.Cu,
referenced to the `In1.Cu` GND plane 0.0994 mm below (εr 3.69), the pair works out to roughly
**87 Ω differential** — inside the 90 Ω ±15 % window. The problem is skew and consistency,
not Z0.

**Fix:** length-match each pair to under 1 mm, equalise via counts, settle the net class on a
single width (0.1554 mm, since that measures correctly) and re-route to it.

## 9. RISK — Switched 3V3 to the TPU is a thin trace

`MCM_3V3` totals 73.8 mm of routing at 0.15–0.2 mm through 6 vias across four layers,
carrying the TPU's entire supply from `U8` (SIP32408 load switch). On the 15 µm inner layers
a 0.15 mm trace is good for roughly 0.5 A; the Edge TPU's peak demand is higher than that.
`U8` also sits 13 mm from `IC2`, whereas Coral places its equivalent (`U21`) 5.5 mm from the
module centre.

Same fix as item 7 — pour `MCM_3V3` and shorten the path.

Related, lower priority: `SDRAM_1V8` is routed at **0.12–0.15 mm** and feeds all of `U7`'s
`VDD` and `VDDQ` balls through the single 0402 ferrite `L3`. The bead itself is correct (see
Cleared item **C3**) and Coral does the same thing through `FB6`, but Coral has plane copper
behind it. Widen this trace.

## 10. RISK — Floating MCU pins

Single-node nets found in the exported netlist. Most are unused peripheral GPIOs, which is
harmless, but these are worth a decision:

| Ball | Signal | Coral does | Note |
|---|---|---|---|
| `U10` | `ONOFF` | routes to B2B `J5.30` | RT1176 has an internal pull-up; leaving it open is acceptable |
| `T8` | `WAKEUP` | `TP9` plus B2B `J5.36` | Confirm against the RT1170 hardware design guide before flight |
| `L13` / `M15` | `LPUART1_TXD/RXD_BT` | via `U14` with 100 kΩ pull-ups | **See item 4 — fix this one** |
| `U9` / `T9` | `PMIC_ON_REQ`, `PMIC_STBY_REQ` | routed | Outputs; safe to leave open |
| `P13` | `GPIO_AD_05` | — | Net is literally named `<NO NET>` — a stray label, worth tidying |

`U4.T11` (`TEST_MODE`) is tied directly to `GND` — correct, and functionally the same as
Coral's resistor to ground.

## 11. RISK — `I2C5_SDA` is in the `90ohmdiff` net class

`sb-tpu.kicad_pro` assigns `I2C5_SDA` to the `90ohmdiff` net class — but not `I2C5_SCL`. I²C
is single-ended, so this gives SDA a 0.0948 mm design width and a differential-pair DRC rule
with no partner. Almost certainly a stray pattern entry. Move it to `Default`.

## 12. RISK — Tactile switch terminal pairing unverified

Both buttons are `SKRPADE010` (Alps SKRP, 4.2 x 3.2 mm, SPST-NO, 4 terminals). The schematic
assumes **pads 1–2 are one common and 3–4 the other**:

* `SW1`: pads 1, 2 → `POR_B`; pads 3, 4 → `GND`
* `SW2`: pads 1, 2 → `DA_nONKEY`; pads 3, 4 → `GND`

The project footprint places pads 1 and 2 on the **left** side and 3 and 4 on the **right**,
consistent with that assumption. The Alps product specification (KRP-703) only says *"1 pole
1 throw — details of contact arrangement are given in the assembly drawings"*, and the
assembly drawing sits behind Alps' members-only area, so this could not be confirmed from
documentation.

**If the internal commons are actually diagonal (1–3 / 2–4), both switches are permanently
closed** — which would hold `POR_B` at ground (MCU in permanent reset) and `DA_nONKEY` at
ground (permanent serial-downloader strap). That failure mode matches "the buttons are wired
incorrectly" precisely.

**Verify on hardware — 30 seconds with a multimeter.** With the board unpowered, measure
continuity across `SW1` pads 1↔2 and 3↔4, then 1↔3 with the button *not* pressed, which must
read **open**. Repeat for `SW2`. Also confirm the `POR_B` pull-up holds about 3 V at `U4.T10`
with nothing pressed.

## 13. RISK — Symbol pin-name errors in the RT1176 symbol

The ball-by-ball diff against Coral found the **electrical connections are correct
everywhere**. These are naming defects in `sb-tpu.kicad_sym` that will mislead future review
and defeat ERC:

| Ball | sb-tpu symbol name | Correct name |
|---|---|---|
| `C16` | `USB2_DP` — **duplicates C17** | `USB2_DN` |
| `J16` | `GPIO_AD_31` — **duplicates J17** | `GPIO_AD_34` |
| `T9` | `PMIC_STY_REQ` | `PMIC_STBY_REQ` |
| `T10` | `POR` | `POR` with overbar (lost in conversion) |
| `G12` | `VDD_USB_3V3` | `VDD_USB_3P3` |

**USB2 polarity is correct** despite the duplicate name: `C16` — physically `USB2_DN` —
connects to `USB2_TPU_N` and on to `IC2` pin 14 (`USB2_D_N`), matching Coral exactly.

## 14. RISK — Non-hermetic tactile switches on a flight board

The Alps SKRPADE010 specification states the part *"does not have sealed structure"*, warns
against use *"in the atmosphere with high humidity or with bedewing probability"*, and
explicitly excludes *"space & aviation devices"* from its qualified applications without
separate verification. Fine for bring-up; flag it for the flight build — conformal coat,
substitute a sealed switch, or depopulate.

## 15. DEFECT — SDRAM bus has a ~19.5 mm length spread across four layers

This confirms the README's *"SDRAM pin layout needs rework for signal integrity"*, with
numbers. Sample of measured routing between `U4` and `U7` (`MT48H32M16LFB4-6`):

| Net | Length | Vias | Layers |
|---|---|---|---|
| `SEMC_CLK` | 8.44 mm | 0 | F.Cu |
| `SEMC_DM1` | 5.42 mm | 2 | In3.Cu |
| `SEMC_A1` | 4.40 mm | 2 | In3.Cu |
| `SEMC_D1` | 14.10 mm | 2 | B.Cu + F.Cu |
| `SEMC_D15` | 12.81 mm | 2 | F.Cu + In2.Cu |
| `SEMC_DM0` | 14.37 mm | 2 | In3.Cu |
| **`SEMC_D0`** | **24.93 mm** | 2 | B.Cu + F.Cu |

Three problems:

* **Skew.** The bus spans 4.40 mm to 24.93 mm — a **19.5 mm spread**, roughly 110 ps —
  against an 8.44 mm clock. `SEMC_D0` alone is 10.8 mm longer than `SEMC_D1` in the same byte
  lane. At the SEMC's operating rate this eats most of the data-valid window.
* **Reference-plane discontinuity.** Nets are scattered over F.Cu, B.Cu, In2.Cu and In3.Cu
  with 0 or 2 vias each. Because there are no power pours (item 7), a net on In2.Cu
  references In1 GND at 0.55 mm while one on In3.Cu references In4 GND at 0.55 mm, and every
  layer change is an uncontrolled return-path discontinuity.
* **Width.** Everything is 0.12 mm — the narrowest on the board.

**Fix:** re-map the pins rather than snaking copper. For SDRAM, **`DQ` bits may be permuted
freely within a byte lane**, and whole byte lanes may be swapped provided each `DQM` follows
its lane — the controller writes and reads the same permutation, so it is invisible to
software. Re-assign `SEMC_D0..D15` to whichever RT1176 balls give the shortest, most equal
routes, keep each byte lane on one layer, and length-match to the clock. Address and control
lines cannot be permuted and must be matched by routing.

## 16. RISK — 11 of 65 3D-model paths point at missing files

Commit `6978607` converted 3D model references from environment variables to relative paths;
all 65 references in `kicad/footprints.pretty/` are now relative, which is the right call.
However, 11 of them resolve to files that are not in `kicad/3dmodels/`:

```
A7101CHUK_T0BC2HAZ.stp     CRCW040247K0JNEDHP.stp    MT29F1G01ABBFDWB-IT_F_TR.stp
BLM21BB121SZ1D.stp         CRCW121010K0JNTA.stp      TL4100AF120QG.stp
CES-104-02-G-S.stp         MC0402N100J250CT.stp      WSLP0603R0100FEA.stp
CES-116-02-G-S.stp         CRCW040210K0FKEE.stp
```

Note `CES-104-02-G-S` and `CES-116-02-G-S` are the header sockets and
`MT29F1G01ABBFDWB-IT_F_TR` is the QSPI NAND — those footprints *are* used on the board, so
the 3D view and any STEP export of the assembly are incomplete.

Separately, a few files are in the wrong directory: `MC0402N100J250CT.stp`,
`LTC4413EDD-1_TRPBF.step` and `LTC4413EDD-1_TRPBF.kicad_sym` are sitting inside
`kicad/footprints.pretty/` rather than `kicad/3dmodels/` and the symbol library.

Cosmetic, but it is the remaining README open item and is cheap to close.

## 17. DEFECT — `EN2` tied to `VSYS`, so Buck 2 never arms soft-start

> **Downgraded from BLOCKER (USB) on 2026-09-28.** See the re-evaluation under "Why the
> board boots from the 3V3 rail but not from USB-C 5V". In short, the LM3370's current limit
> is cycle-by-cycle, not foldback. The real load is ~20–25 µF, not ~50 µF (item 21), so a hard
> start completes in ~0.1 ms. That is well inside the 2.0 ms `DCDC_IN` rule, which was also
> validated on the logic analyzer. The paragraphs below that predict foldback and a
> `DCDC_IN` ramp violation are superseded. The fix itself still stands.

From the LM3370 datasheet (SNVS406N): *"Soft start is activated only if EN goes from logic
low to logic high **after V_IN reaches 2.7 V**."*

`IC1` pin 15 (`EN2`) is tied directly to `VSYS`, which is also `VIN1`, `VIN2` and `VDD`. As
`VSYS` ramps, `EN2` passes the 1.0 V `V_IH` threshold at about 1.0 V — well below the 2.7 V
UVLO. By the time the part is permitted to switch, `EN2` has *already* been high for some
time, so the low-to-high transition the soft-start circuit looks for never occurs after
`VIN` > 2.7 V. **Channel 2 starts with no inrush limiting.**

Channel 1 does not have this problem: `EN1` is driven through `R2` 47 kΩ / `C17` 1 µF, so it
transitions roughly 11–17 ms after `VSYS` (recomputed at the datasheet's 1.0 V threshold:
11.4 ms from 4.65 V on USB, 17.3 ms from 3.25 V on rail). That correctly arms soft-start for
the 1.8 V rail. The same protection was simply never applied to the 3.3 V rail.

**Why it only bites on USB:** on rail power `U1` selects the bus `+3V3` directly, so Buck 2
starts into essentially no load and the missing soft-start is harmless. On USB, Buck 2 must
charge the whole 3.3 V domain — `VDD_3V3` decoupling plus `C45` 22 µF and `C48` 4.7 µF on
`MCU_DCDC_IN`, roughly 50 µF — against a peak switch current limit of **850 mA minimum**.
That produces current-limit foldback, a slow or stalled `MCU_DCDC_IN` ramp, and possibly a
restart loop.

It also breaks the `DCDC_PSWITCH` timing rule. With `R38` = 30 kΩ and `C55` = 0.22 µF the
PSWITCH RC is **6.6 ms**, so NXP requires `DCDC_IN` to reach full within
**0.3 × 6.6 ≈ 2.0 ms**. Charging ~50 µF at a current-limited rate can easily exceed that.

**Fix:** give `EN2` its own RC from `VSYS` — the same topology as `EN1` but faster, so 3.3 V
still leads 1.8 V. Something like 10 kΩ with 0.1 µF (about 1 ms to the 1.0 V threshold) both
arms soft-start and preserves the sequencing. Add a discharge diode as `D5` does for `EN1`.

## 18. DEFECT — `IC1` `SDA` and `SCL` are left floating

The LM3370 datasheet states plainly: *"When not using I²C the SDA and SCL pins should be tied
directly to the VDD pin."*

In this design `IC1` pin 10 (`SDA`) and pin 11 (`SCL`) are both **no-connect** — they appear
in the netlist as `unconnected-(IC1-SDA-Pad10)` and `unconnected-(IC1-SCL-Pad11)`.

These are not inert pins. The LM3370's I²C registers hold, among other things, the per-channel
enable bits (`EN1` and `EN2`, both defaulting to 1), the output-voltage selection codes, the
forced-PWM bits and a `DISPOR` bit that can disable the power-on-reset function entirely.
Floating CMOS inputs sitting next to a 2 MHz switching converter are a plausible route to
spurious register activity, and at minimum raise quiescent current from input-stage crowbar.

There is an interesting asymmetry here too: **on rail power Buck 2 sits at 100 % duty and does
not switch**, so there is far less local switching noise than on USB power, where it runs at
2 MHz. That makes this a candidate contributor to the USB-only failure as well.

**Fix:** tie `IC1` pins 10 and 11 to `VSYS` (the `VDD` pin's net). Two 0 Ω links or direct
connections. This is cheap and should be done regardless of whether it turns out to be
causal.

## 19. DEFECT — On USB, the entire 3.3 V load passes through Buck 2's ~0.85 A limit

The LM3370's `ILIM` peak switching current limit is specified as **850 mA minimum**,
1200 mA typical, 1400 mA maximum, per channel.

On USB power, Buck 2 is the sole source for:

* the MCU's `VDD_3V3` domains, plus `VDDA_ADC_3P3` and `VDD_USB_3V3` through `L6` and `L8`
* `MCU_DCDC_IN` through `R34`, which feeds the RT1176's internal DCDC and therefore
  `VDD_SOC_IN`
* **`MCM_3V3` through `U8`** — the entire Edge TPU

The TPU's transient demand on its own approaches that limit (which is why item 7 matters), so
the combined draw is over budget. On rail power none of this current goes through `IC1` at
all, which is precisely why the problem is invisible there.

**Fix options:** keep the TPU off while on USB power (firmware gate on `TPU_POW_EN`, which is
already MCU-controlled); or treat USB as a programming and debug supply only and document
that the TPU requires rail power; or move to a 3.3 V converter sized for the full load. This
is a specification decision, not a wiring error — but it should be written down, because the
current design implies USB can run the whole board and it cannot.

## 20. DEFECT — On rail power Buck 2 runs in dropout, and `nPOR2` can assert `POR_B`

The mirror image of the previous items. `IC1` pins 12 and 13 (`nPOR1`, `nPOR2`) are open-drain
outputs tied to `POR_B`, and per the datasheet they *"pull low when the outputs are below 94 %
(rising V_OUT) or 85 % (falling V_OUT) of the desired output"*, with roughly 50 ms of delay
before release.

`nPOR2` monitors Buck 2, whose target is 3.3 V — so its rising release threshold is
**3.10 V**. On rail power `VSYS` is only about 3.25 V, so Buck 2 sits at 100 % duty (the part
supports this as a low-dropout mode) and its output is
`VSYS − I_LOAD × (R_DSON,PFET + R_INDUCTOR)`. With `R_DSON` up to 500 mΩ plus the inductor's
DCR, even a modest load on `VDD_3V3_SENSE` pulls the output below 3.10 V.

`VDD_3V3_SENSE` is lightly loaded — `U1`'s `INA` input, `C9` and `TP2` — so at present it
probably stays just above threshold, which is consistent with the board booting on rail power
once the watchdog was removed. But the margin is small and temperature-dependent, and if it
ever dips, **`nPOR2` pulls `POR_B` low and resets the MCU.** That is a second latent reset
source of exactly the kind item 1 turned out to be.

**Fix:** disable Buck 2 when the board is running from the bus rail — gate `EN2` rather than
tying it to `VSYS`, which the item 17 fix already requires touching. Alternatively set
`DISPOR` via I²C, but that needs the `SDA`/`SCL` connections from item 18 and firmware, so
gating `EN2` is simpler. At minimum, measure `VDD_3V3_SENSE` at `TP2` on rail power and
confirm the margin above 3.10 V.

## 21. BLOCKER (USB) — `MCU_DCDC_IN` decoupling does not return to ground

Found during the 2026-09-28 re-evaluation. Present in both the schematic (`RT1176_1`) and
`sb-tpu.kicad_pcb`:

| Cap | Value | Pad on `MCU_DCDC_IN` | Other pad |
|---|---|---|---|
| `C45` | 22 µF | 1 | `Net-(C45-Pad2)` |
| `C46` | 0.1 µF | 2 | `Net-(C45-Pad2)` |
| `C48` | 4.7 µF | 2 | `Net-(C45-Pad2)` |

`Net-(C45-Pad2)` has exactly those three pads and nothing else. With both ends of all three
caps on the same pair of nets, they do nothing. **`DCDC_IN` (`U4.L5`, `M5`, `N5`) has zero
local capacitance to `GND`.** The nearest real capacitance is `C3` 4.7 µF on `VDD_3V3`,
behind `R34` 0.1 Ω and `U1`.

**Consequence:** the RT1176's internal DCDC draws its pulsed input current through trace
inductance and an ideal-diode OR. On the stiff bus rail this is tolerated. When Buck 2 is
the only source (USB power), a `DCDC_IN` dip at `DCDC_PSWITCH` enable, or a `VDD_3V3_SENSE`
dip below 85 % that trips `nPOR2`, is a credible cause of the USB-only start failure.

**Bodge:** wire the `C45`/`C46`/`C48` common node to the nearest `GND` via.
**Fix:** reconnect those pads to `GND` in the schematic. It is probably a missing ground
symbol or a dangling wire on `RT1176_1`.

---

# Cleared — investigated, no defect found

These were on the suspect list. They were checked against Coral and are **correct**. Do not
spend rework effort here.

## C1. Boot-mode and `BT_CFG` straps match Coral exactly

`BOOT_MODE[1:0]` defaults to **`10` = Internal Boot**, and becomes **`01` = Serial
Downloader** while `SW2` is held — the intended behaviour, implemented identically to Coral:

* Idle: `R51` 4.7 kΩ pulls `BOOT_MODE1` to 1.8 V → `Q2` on → `BOOT_MODE0` pulled to about
  38 mV through `R53` 100 Ω against `R52` 4.7 kΩ. Solid `10`.
* `SW2` pressed: `D8` pulls `BOOT_MODE1` low → `Q2` off → `BOOT_MODE0` rises to 1.8 V. `01`.

The 12 `BT_CFG` straps also match Coral's **fitted** population bit for bit:

| Strap | Coral fitted | sb-tpu | Level |
|---|---|---|---|
| `BT_CFG1_0` … `_5` | 47 kΩ pull-down (`R151`–`R156`) | 47 kΩ pull-down (`R4`, `R6`, `R8`, `R11`, `R13`, `R15`) | **L** |
| `BT_CFG1_6`, `_7` | 4.7 kΩ pull-up to `DCDC_1V8_OUT` (`R145`, `R146`) | 4.7 kΩ to `DCDC_1V8_OUT` (`R16`, `R18`) | **H** |
| `BT_CFG2_0`, `_1`, `_3` | 47 kΩ pull-down (`R159`, `R160`, `R162`) | 47 kΩ pull-down (`R21`, `R23`, `R27`) | **L** |
| `BT_CFG2_2` | 4.7 kΩ pull-up (`R149`) | 4.7 kΩ to `DCDC_1V8_OUT` (`R24`) | **H** |

Ball assignments match too — for example `BT_CFG1_5` on `A14` and `BT_CFG1_2` on `A15`.

**The README's "NXP boot pin is unstrapped" is not supported by the netlist.** The real
boot-path gap is the missing UART isolation, item 4.

## C2. TPU module strapping is correct, with one exception

Full pin-by-pin comparison of `IC2` (sb-tpu) against `U23` (Coral):

| Pin | Function | Coral (fitted) | sb-tpu | Verdict |
|---|---|---|---|---|
| 13 / 14 | `USB2_D_P` / `_N` | `R132` / `R133` 0 Ω to MCU | direct to MCU `C17` / `C16` | polarity correct |
| 49 / 50 | `I2C_SDA` / `SCL` | to MCU I²C5 | via `IC5` bilateral switch to I²C5 | ok |
| 53 | `PMIC_EN` | `R138` **0 Ω** → `MCM_1V8` | direct to `MCM_1V8` | equivalent |
| 54 | `AON` | `R137` **0 Ω** → `MCM_1V8` | direct to `MCM_1V8` | equivalent |
| 56–67 | `VIN` x12 | `MCM_3V3` | `MCM_3V3` | ok |
| 76 | `RST_L` | `R136` 10 kΩ pull-down plus MCU | `R28` 10 kΩ pull-down plus MCU `M4` | ok |
| 82 | `SD_ALARM` | to MCU | to MCU `L4` | ok |
| 83 | `USB_SEL` | `R110` **0 Ω to 1V8, fitted**; `R125` 10 kΩ pull-down **DNP** → **HIGH** | direct to `MCM_1V8` → **HIGH** | ok |
| 84 | `BT_PHY_PRG` | `R116` pull-up **DNP**; `R129` 10 kΩ pull-down **fitted** → **LOW** | `R29` 10 kΩ pull-down → **LOW** | ok |
| 85 | `BOOT_FAIL` | to test point | to MCU `K5` | ok (improvement) |
| 37, 52, 77, 78 | `PGOOD4`, `PMIC_INT`, `INTR`, `CLKREQ_L` | test points only | no-connect | ok |
| **4, 5** | **`PCIE_TX_N/P`** | **no-connect** | **GND** | **see item 2** |

`USB_SEL` and `BT_PHY_PRG` in particular *look* different on paper, because Coral draws both
a pull-up and a pull-down for each — but with the DNP variant applied, the resulting logic
levels are identical to `sb-tpu`.

Also correct: the local 1.8 V generation (`IC3` NCP170ASN180T2G, enabled by `R30` 10 kΩ from
`MCM_3V3`) mirrors Coral's `U22`; the load switch `U8` (SIP32408) mirrors Coral's `U21`; and
`U4.P2` (`GPIO_EMC_B2_16`) tied to `MCM_1V8` as a rail-present sense matches Coral exactly.

## C3. Ferrite beads are correctly specified

All six beads are `BLM15AG121SN1D`: **120 Ω at 100 MHz, 0402, 500 mA rated, 190 mΩ DCR,
−55 to +125 °C**. Coral's part is specified as *"FERRITE, BEAD, 120 OHMS@100MHZ, 25%, 550mA,
190 mOHM DCR, 0402"* — the same impedance, size, DCR and current class. The project footprint
`IND_BLM15_0402_MUR` is a correct 0402 land, with pads at ±0.52 mm.

The topology is a one-for-one match as well:

| Rail | Coral | sb-tpu |
|---|---|---|
| `VDDA_ADC_3P3` from `VDD_3V3` | `FB1` | `L6` |
| `ADC_1V8_IN` from `DCDC_1V8_OUT` | `FB2` | `L5` |
| `VDD_MIPI_1P8` from `VDD_1V8` | `FB3` | `L9` |
| `VDD_USB_1P8` from `VDD_1V8` | `FB4` | `L7` |
| `VDD_USB_3P3` from `VDD_3V3` | `FB5` | `L8` |
| `SDRAM_1V8` from `VDD_1V8` | `FB6` | `L3` |

**No action on the beads themselves.** The only related item is the thin `SDRAM_1V8` trace
downstream of `L3` — see item 9.

## C4. TPU decoupling count and values match Coral

Comparing fitted parts only, `MCM_3V3` gets 2 x 22 µF plus 6 x 0.1 µF (plus 1 µF) on
`sb-tpu`, against 2 x 22 µF plus 6–7 x 0.1 µF on Coral. Coral's four 100 µF and two extra
22 µF are all marked **DNP**. The bill of materials is right; only the **placement** is
wrong — item 7.

One watch item: `C42` and `C43` are `GRM158R61A226ME15D`, 22 µF 10 V in an **0402** body,
against Coral's 0603. DC-bias derating on 0402 22 µF parts is severe, often over 50 % at
3.3 V, so expect closer to 8–10 µF effective each. Worth measuring, or moving to 0603.

## C5. The I²C isolation switch `IC5` is correct

`IC5` is `74LVC2G66GT,115`. Verified against the Nexperia datasheet, rev. 14:

* Ordering code `GT` = **XSON8, SOT833-1** — and the assigned footprint
  `74AVC9112GTX.kicad_mod` carries `descr "SOT833-1"` with 0.5 mm pitch. **The package
  matches**, despite the misleading filename.
* The SOT833-1 pin map is `1=1Y, 2=1Z, 3=2E, 4=GND, 5=2Y, 6=2Z, 7=1E, 8=VCC` — **exactly the
  schematic symbol**.
* **`nE` is active HIGH** (`H` = ON-state). Tying `1E` and `2E` to `MCM_1V8` correctly closes
  the I²C bridge only once the TPU's own 1.8 V rail is alive.
* `VCC` is `VDD_1V8`, and the enable pins are characterised for input voltage at `VCC = 0 V`,
  so the cross-domain enable is safe.
* I²C pull-ups exist on the MCU side: `R46` and `R47`, 2.2 kΩ to `VDD_1V8`. Because the '66 is
  a bidirectional analog switch with about 7 Ω on-resistance, pull-ups on one side only is
  correct.

## C6. The power *architecture* is sound (but see items 17–20 for its details)

The topology below is correct and meets the dual-input requirement. The problems found later
are in how `IC1` is configured and loaded, not in the ORing scheme itself.

| Node | Implementation | Assessment |
|---|---|---|
| `VSYS` | `U2` LTC4413 ideal-diode OR of `VSYS_5V` (USB) and `+3V3` (bus rail) | meets the dual-input requirement |
| `VSYS_5V` | `D2` RBS2MM40 (2 A, low Vf) from `VUSB` | back-power block |
| `VDD_1V8` / `VDD_3V3_SENSE` | `IC1` LM3370 dual buck from `VSYS`, `L1` / `L2` 2.2 µH | ok |
| Sequencing | Channel 2 (3V3) `EN2` direct to `VSYS`; channel 1 (1V8) `EN1` via `R2` 47 kΩ and `C17` 1 µF with `D5` discharge | Order is correct — 3V3 before 1V8 — and `EN1`'s delay is 11–17 ms at the datasheet's 1.0 V threshold. **But `EN2` being static breaks Buck 2's soft-start; see item 17** |
| `VDD_3V3` | `U1` LTC4413 ideal-diode OR of the buck output and the raw `+3V3` bus rail | this is what lets the board run from a 3.3 V rail the buck could not step down |
| `VDD_SNVS_IN` | `VLDO_3V3` = Schottky OR: `D3` from `+3V3`, `D4` from `U3` TCR2LN33 off `VSYS_5V` | always-on domain comes up before `DCDC_IN` |

Two minor observations, neither a defect:

* `D1` (CDBQC0240L, 200 mA) sits in **parallel** with `U1`'s channel-B ideal diode from
  `+3V3` to `VDD_3V3`. It only conducts if the LTC4413 drop exceeds about 0.4 V, which needs
  well over 2 A, so it is effectively inert — but it is a 200 mA part bridging a rail that can
  carry around 1 A, and it adds leakage and junction capacitance. Consider removing it or
  up-rating it.
* When running from the 3.3 V bus alone, `VSYS` is about 3.25 V and buck channel 2 cannot
  regulate to 3.3 V; it runs at roughly 100 % duty and is de-selected by `U1` in favour of the
  direct rail. That is the intended behaviour, but it means channel 2 dissipates for no
  benefit in rail-only operation. Consider gating `EN2` when USB is absent.

## C7. Other checks that came back clean

* **RT1176 ball map:** all 289 balls compared against Coral. Every net assignment for power,
  analog, DCDC, crystal and USB pins matches. Only naming differs — item 13.
* **USB PHY supplies:** `VDD_USB_3V3` (`G12`) and `VDD_USB_1P8` (`H12`) are correctly fed
  through `L8` and `L7` with local caps, the same as Coral's `FB5` and `FB4`. Not a cause of
  the USB failure.
* **`USB2_VBUS`** (`D16`) goes to `MCM_3V3` — matches Coral.
* **Footprint pad counts** verified for `IC2` (120), `U8` (5 = TDFN-4 plus thermal), `IC7`
  (5 = SOT-353), `IC5` (8) and the ferrite beads (0402).
* **Differential-pair impedance** on the routed geometry computes to about 87 Ω differential
  — in spec.
* **`TEST_MODE`** grounded, and the **ADC divider** (`R41` 20 kΩ / `R42` 10 kΩ, giving 1.67 V
  from 5 V) matches its schematic note.

---

# Recommended order of work

1. ~~Depopulate `U5`~~ — **done**, and it let the board boot. Item 1 is closed on hardware;
   it still needs fixing in the schematic so it does not return on the next build.
2. **Tie `IC1` pins 10 and 11 to `VSYS`** — item 18. Cheap, datasheet-mandated, and a possible
   contributor to the USB-only failure.
3. **Ground the `C45`/`C46`/`C48` common node** and retry USB power — item 21. This is now
   the leading explanation for USB-C not booting. Capture `MCU_DCDC_IN`, `TP2`, `POR_B` and
   `DCDC_PSWITCH` on that attempt, and run `bringup/TPU_power_phasing.py` against it for the
   SNVS ordering.
4. **Assert `TPU_POW_EN` on USB power** and watch `VDD_3V3_SENSE` and `POR_B` — item 19. If the
   rail collapses, this needs a respin decision. Re-time `EN2` (item 17) only if USB start-up
   still fails after step 3.
5. ~~Bodge `IC7.5` to `VUSB`~~ — superseded: `PORT` is tied low in `63e516a` (item 3).
6. **Verify the switch pinout** with a multimeter — item 12. Two minutes, and it either
   confirms or eliminates the button complaint.
7. **Add the two 100 kΩ pull-ups** on `LPUART1_*_BT` and retry USB boot — item 4.
8. **Measure `VDD_3V3_SENSE` at `TP2` on rail power** and confirm margin above 3.10 V —
   item 20.
9. Only then re-evaluate the USB2-to-TPU link. If it still fails with the board stable, the
   remaining suspects are the pair skew (item 8) and TPU rail collapse (items 7 and 9).

**Respin list:** item 2 (lift `IC2` pins 4 and 5), item 5 (`DA_nONKEY` pull-up), item 6
(`POR_B` cap), items 7 and 9 (power pours and bulk placement), item 8 (pair matching),
item 15 (SDRAM pin re-map), item 11 (net class), item 13 (symbol names), item 16 (3D models),
items 17, 18 and 20 (`EN2` timing, `SDA`/`SCL` tie-off, Buck 2 gating on rail power), item 21
(`DCDC_IN` caps to `GND`), and a
decision on item 19 (whether USB is ever expected to run the TPU).

## Coverage against the README's open-items list

| README item | Status here |
|---|---|
| "USB communication not initializing to the Coral module" | Items 1, 3, 8; cleared in C7 for the PHY supplies |
| "NXP boot pin is unstrapped; requires jumper wiring" | **Reworded** — straps are correct (C1); the real gap is item 4 |
| "SDRAM pin layout needs rework for signal integrity" | Item 15, quantified |
| "General PCB layout cleanup" | Items 7, 8, 9, 11, 15 |
| "Some 3D models may reference out-of-date paths" | Item 16 — now relative, but 11 targets missing |

---

## References

* TI **TPS3813** datasheet, SLVS331J — <https://www.ti.com/lit/ds/symlink/tps3813.pdf>
* TI **LM3370** datasheet, SNVS406N — <https://www.ti.com/lit/ds/symlink/lm3370.pdf>
* NXP **PTN5150A** datasheet rev. 1 — <https://www.nxp.com/docs/en/data-sheet/PTN5150A.pdf>
* Nexperia **74LVC2G66** datasheet rev. 14 — <https://assets.nexperia.com/documents/data-sheet/74LVC2G66.pdf>
* Murata **BLM15AG121SN1D** — <https://www.mouser.com/en/ProductDetail/Murata-Electronics/BLM15AG121SN1D>
* Alps **SKRPADE010** product page and specification KRP-703 — <https://tech.alpsalpine.com/e/products/detail/SKRPADE010/>

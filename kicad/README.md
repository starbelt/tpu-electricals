# KiCad Project — sb-tpu

The `sb-tpu` KiCad 8 project: schematics, PCB layout, project libraries, and manufacturing outputs for the board described in the [top-level README](../README.md).

## Opening the project

Open `sb-tpu.kicad_pro` in KiCad. The project-local footprint (`fp-lib-table`) and symbol (`sym-lib-table`) tables point at [footprints.pretty/](footprints.pretty/) and `sb-tpu.kicad_sym`, so no extra library setup should be needed.

## Schematic hierarchy

`sb-tpu.kicad_sch` is the root sheet and includes:

* `TPU.kicad_sch` — Coral Edge TPU module circuitry
* `IO.kicad_sch` — external I/O
* `Power_Sys.kicad_sch` — DCDC power supplies and sequencing
* `BOOT.kicad_sch` — MCU boot-strapping circuit
* `RT1176.kicad_sch` — NXP i.MX RT1176 MCU, split across `RT1176_1.kicad_sch`, `RT1176_2.kicad_sch`, `RT1176_3.kicad_sch`

`NXP.kicad_sch` also exists in this folder but is not currently wired into the root sheet hierarchy.

## Subdirectories

* [3dmodels/](3dmodels/) — STEP models referenced by project footprints
* [footprints.pretty/](footprints.pretty/) — project-local footprint library
* [production/](production/) — manufacturing exports (BOM, placement, netlist, fab archives)

`sb-tpu-backups/` (local KiCad auto-backups) is git-ignored and won't appear in a fresh clone.

## Manufacturing

`fabrication-toolkit-options.json` configures the [Fabrication Toolkit](https://github.com/bennymeg/Fabrication-Toolkit) KiCad plugin used to generate the exports under [production/](production/), which target JLCPCB/LCSC part numbers.

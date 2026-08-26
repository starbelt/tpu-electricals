# Bring-Up

Scripts and captured data used to validate the `sb-tpu` power-sequencing requirements against a [Saleae](https://www.saleae.com/) logic analyzer capture.

## Contents

* `TPU_power_phasing.py` — parses a Saleae CSV export and checks the DCDC/power-switch sequencing against the NXP i.MX RT1176 power-up requirements:
  * `VDD_SNVS_IN` must come up before `DCDC_IN`
  * `DCDC_PSWITCH` must trail `DCDC_IN` by at least 1 ms
  * `VDD_1V8` must come up after `DCDC_PSWITCH`
  * `DCDC_IN`'s ramp time must stay within 0.3 × RC of the measured pswitch RC delay
* `*.sal` — raw Saleae capture files, viewable in the [Saleae Logic 2](https://www.saleae.com/downloads/) application
* `*.csv` — CSV exports of the above captures, consumed by `TPU_power_phasing.py` (not tracked in git — regenerate by exporting the corresponding `.sal` capture from Logic 2)

## Usage

```bash
pip install pandas
python TPU_power_phasing.py
```

The script currently points at `dcdc_pswitch_1v8.csv`; edit the filepath at the bottom of the script to check a different capture.

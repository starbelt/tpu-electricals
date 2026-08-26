# Production

Manufacturing outputs for `sb-tpu`, generated from the KiCad project via the [Fabrication Toolkit](https://github.com/bennymeg/Fabrication-Toolkit) plugin (see `../fabrication-toolkit-options.json`) and targeting JLCPCB/LCSC fabrication and assembly.

## Contents

* `netlist.ipc` — IPC-D-356 netlist, for electrical test / bare-board verification
* `sb-tpu.zip` — Gerbers, drill files, and fab-ready manufacturing archive
* `sb-tpu-odb.zip` — ODB++ format export of the same design
* `backups/` — see [backups/README.md](backups/README.md)

`bom.csv`, `designators.csv`, and `positions.csv` (bill of materials, reference designators, and pick-and-place coordinates) are also generated here but are git-ignored — regenerate them from KiCad via the Fabrication Toolkit plugin rather than pulling them from git history.

These files are generated, not hand-edited — regenerate rather than editing directly whenever the schematic or layout changes.

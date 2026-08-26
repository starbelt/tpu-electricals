# TPU-Electricals

Open source hardware design for `sb-tpu`, a board embedding a Google Coral Edge TPU alongside an NXP i.MX RT1176 MCU, targeted at picosatellite payloads. Designed in [KiCad](https://www.kicad.org/).

## Status

This is an active, evolving design — treat it as a reference, not a finished/validated product. See [Open Items](#open-items) below before building.

## Open Items

* USB communication not initializing to the Coral module
* NXP boot pin is unstrapped; requires jumper wiring for a proper boot sequence
* SDRAM pin layout needs rework for signal integrity
* General PCB layout cleanup
* Some 3D models may reference out-of-date paths

## Directory Contents

* [bringup/](bringup/): Bring-up validation scripts and captured logic-analyzer data for power sequencing
* [kicad/](kicad/): KiCad project — schematics, PCB layout, libraries, and manufacturing outputs
* [scripts/](scripts/): Standalone helper scripts for managing KiCad libraries

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 Jack Rathert.

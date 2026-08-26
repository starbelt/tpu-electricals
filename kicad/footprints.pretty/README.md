# footprints.pretty

Project-local KiCad footprint library for `sb-tpu`, referenced by the project's `fp-lib-table` under the `footprints` nickname. Contains custom and distributor-sourced footprints (BGA, QFN, DFN, SOT, chip R/C, connectors, test points, mounting holes, etc.) not covered by KiCad's standard libraries.

Populated/updated via [../../scripts/extract_footprints.py](../../scripts/extract_footprints.py), which flattens downloaded component libraries into this folder and links their footprint references from the symbol side.

3D models referenced by these footprints live in [../3dmodels/](../3dmodels/).

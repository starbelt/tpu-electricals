import os
import re
import shutil
from pathlib import Path


def extract_and_map_footprints(src_dir, dest_dir):
    """Copy all .kicad_mod files flat into dest_dir. No renaming or deduplication."""
    src = Path(src_dir)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    mapping = {}  # src_path -> filename
    copied = 0

    for root, _, files in os.walk(src):
        for f in files:
            if not f.lower().endswith(".kicad_mod"):
                continue

            src_file = Path(root) / f
            dest_file = dest / f
            shutil.copy2(src_file, dest_file)
            mapping[src_file.resolve()] = f
            copied += 1

    print(f"Copied {copied} footprints → {dest.resolve()}")
    return mapping


def link_symbols_by_folder(base_dir, lib_name, mapping):
    """Set (property "Footprint" "<lib_name>:<footprint>") for all symbols in same folder."""
    base = Path(base_dir)
    linked = 0

    for root, _, files in os.walk(base):
        root_path = Path(root)
        sym_files = [f for f in files if f.endswith(".kicad_sym")]
        fp_files = [f for f in files if f.endswith(".kicad_mod")]
        if not sym_files or not fp_files:
            continue

        chosen_fp = Path(fp_files[0])
        src_fp_path = (root_path / chosen_fp).resolve()
        final_fp_name = mapping.get(src_fp_path, chosen_fp.name)
        footprint_ref = f"{lib_name}:{Path(final_fp_name).stem}"

        for sym_file in sym_files:
            sym_path = root_path / sym_file
            text = sym_path.read_text(encoding="utf-8")

            # Replace or insert Footprint property
            if re.search(r'\(property\s+"Footprint"\s+"[^"]*"\)', text):
                new_text = re.sub(
                    r'\(property\s+"Footprint"\s+"[^"]*"\)',
                    f'(property "Footprint" "{footprint_ref}")',
                    text,
                    count=1,
                )
            else:
                new_text = re.sub(
                    r'(\(symbol\s+"[^"]+"\s*\n)',
                    r'\1  (property "Footprint" "' + footprint_ref + '")\n',
                    text,
                    count=1,
                )

            sym_path.write_text(new_text, encoding="utf-8")
            linked += 1
            print(f"Linked: {sym_path} → {footprint_ref}")

    print(f"Updated {linked} symbol files with new footprint references.")


if __name__ == "__main__":
    components_root = Path("C:/Users/jackr/Downloads/Components")
    footprints_target = Path("C:/Users/jackr/Repos/tpu-electricals/kicad/footprints.pretty")
    lib_nickname = "footprints"

    mapping = extract_and_map_footprints(components_root, footprints_target)
    link_symbols_by_folder(components_root, lib_nickname, mapping)

import os
import re
import shutil
import hashlib
from pathlib import Path

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_and_map_footprints(src_dir, dest_dir):
    """Flatten all .kicad_mod files, deduplicate by content, and record mapping."""
    src = Path(src_dir)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    seen_hashes = {}
    mapping = {}  # src_path -> final filename
    copied = 0

    for root, _, files in os.walk(src):
        for f in files:
            if not f.lower().endswith(".kicad_mod"):
                continue

            src_file = Path(root) / f
            file_hash = hash_file(src_file)
            base = Path(f).stem
            ext = ".kicad_mod"

            # If identical content already exists, reuse that name
            if file_hash in seen_hashes:
                mapping[src_file.resolve()] = seen_hashes[file_hash]
                continue

            dest_file = dest / f
            if dest_file.exists() and hash_file(dest_file) != file_hash:
                i = 1
                while True:
                    candidate = dest / f"{base}_{i}{ext}"
                    if not candidate.exists():
                        dest_file = candidate
                        break
                    i += 1

            shutil.copy2(src_file, dest_file)
            seen_hashes[file_hash] = dest_file.name
            mapping[src_file.resolve()] = dest_file.name
            copied += 1

    print(f"Copied {copied} unique footprints → {dest.resolve()}")
    return mapping


def link_symbols_by_folder(base_dir, lib_name, mapping):
    """Insert (property "Footprint" "<lib_name>:<footprint>") for symbols in same folder."""
    base = Path(base_dir)
    linked = 0
    skipped = 0

    for root, _, files in os.walk(base):
        root_path = Path(root)
        sym_files = [f for f in files if f.endswith(".kicad_sym")]
        fp_files = [f for f in files if f.endswith(".kicad_mod")]
        if not sym_files or not fp_files:
            continue

        # Pick first footprint, then map to renamed filename if available
        chosen_fp = Path(fp_files[0])
        src_fp_path = (root_path / chosen_fp).resolve()
        final_fp_name = mapping.get(src_fp_path, chosen_fp.name)
        footprint_ref = f"{lib_name}:{Path(final_fp_name).stem}"

        for sym_file in sym_files:
            sym_path = root_path / sym_file
            text = sym_path.read_text(encoding="utf-8")

            # Skip if already has a Footprint property
            if re.search(r'\(property\s+"Footprint"\s+"[^"]*"\)', text):
                skipped += 1
                continue

            new_text = re.sub(
                r'(\(symbol\s+"[^"]+"\s*\n)',
                r'\1  (property "Footprint" "' + footprint_ref + '")\n',
                text,
                count=1,
            )
            sym_path.write_text(new_text, encoding="utf-8")
            linked += 1
            print(f"Linked: {sym_path} → {footprint_ref}")

    print(f"Linked {linked} symbols, skipped {skipped} (already had footprints)")


if __name__ == "__main__":
    components_root = Path("C:/Users/jackr/Downloads/Components")
    footprints_target = Path("C:/Users/jackr/Repos/tpu-electricals/kicad/footprints.pretty")
    lib_nickname = "footprints"  # must match KiCad library nickname

    mapping = extract_and_map_footprints(components_root, footprints_target)
    link_symbols_by_folder(components_root, lib_nickname, mapping)

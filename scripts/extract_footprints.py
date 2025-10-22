import os, re
import shutil
import hashlib
from pathlib import Path

def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_unique_footprints(src_dir, dest_dir):
    src = Path(src_dir)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    copied = 0
    skipped = 0
    scanned_dirs = 0

    for root, _, files in os.walk(src):
        scanned_dirs += 1
        print(f"Scanning: {root}")

        for f in files:
            if not f.lower().endswith(".kicad_mod"):
                continue

            src_file = Path(root) / f
            try:
                file_hash = hash_file(src_file)
            except Exception as e:
                print(f"Error reading {src_file}: {e}")
                continue

            if file_hash in seen_hashes:
                skipped += 1
                continue

            seen_hashes.add(file_hash)
            dest_file = dest / f

            if dest_file.exists() and hash_file(dest_file) != file_hash:
                base = dest_file.stem
                ext = dest_file.suffix
                i = 1
                while True:
                    candidate = dest / f"{base}_{i}{ext}"
                    if not candidate.exists():
                        dest_file = candidate
                        break
                    i += 1

            shutil.copy2(src_file, dest_file)
            copied += 1

    print(f"\nScanned {scanned_dirs} directories.")
    print(f"Copied {copied}, skipped {skipped}, total unique: {copied}")
    print(f"Output: {dest.resolve()}")



def link_symbols_by_folder(base_dir, lib_name):
    base = Path(base_dir)

    for root, _, files in os.walk(base):
        root_path = Path(root)
        symbols = [f for f in files if f.endswith(".kicad_sym")]
        footprints = [f for f in files if f.endswith(".kicad_mod")]

        if not symbols or not footprints:
            continue  # Skip folders without both types

        chosen_fp = Path(footprints[0]).stem  # take first footprint in the folder
        footprint_ref = f"{lib_name}:{chosen_fp}"

        for sym_file in symbols:
            sym_path = root_path / sym_file
            text = sym_path.read_text(encoding="utf-8")

            # Check if "Footprint" already exists
            if re.search(r'\(property\s+"Footprint"\s+"[^"]*"\)', text):
                print(f"Skip (already linked): {sym_path}")
                continue

            # Insert new property after (symbol ...)
            new_text = re.sub(
                r'(\(symbol\s+"[^"]+"\s*\n)',
                r'\1  (property "Footprint" "' + footprint_ref + '")\n',
                text,
                count=1,
            )

            sym_path.write_text(new_text, encoding="utf-8")
            print(f"Linked: {sym_path} -> {footprint_ref}")




if __name__ == "__main__":
    components = "C:/Users/jackr/Downloads/Components"
    footprints_target = "C:/Users/jackr/Repos/tpu-electricals/kicad/footprints.pretty"
    extract_unique_footprints(components, footprints_target)


    lib_nickname = "footprints"  # match KiCad library nickname
    link_symbols_by_folder(components, lib_nickname)

import os
import shutil
from pathlib import Path

def extract_footprints(src_dir, dest_dir):
    src = Path(src_dir)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    name_counts = {}
    copied = 0

    for root, _, files in os.walk(src):
        for f in files:
            if not f.endswith(".kicad_mod"):
                continue

            src_file = Path(root) / f
            base_name = Path(f).stem
            ext = Path(f).suffix

            # Count duplicates
            count = name_counts.get(base_name, 0)
            name_counts[base_name] = count + 1

            # Create unique destination name
            if count == 0:
                dest_file = dest / f
            else:
                dest_file = dest / f"{base_name}_{count}{ext}"

            shutil.copy2(src_file, dest_file)
            copied += 1

    print(f"Copied {copied} footprint files to {dest.resolve()}")

# Example usage:
# extract_footprints(r"C:\path\to\components_master", r"C:\path\to\footprints_only")

if __name__ == "__main__":

    components = "C:/Users/jackr/Downloads/Components"
    footprints_target = "C:/Users/jackr/Repos/tpu-electricals/kicad/footprints.pretty"
    extract_footprints(components, footprints_target)
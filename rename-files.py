#!/usr/bin/env python3
"""
rename_files.py

Renames all files in a given folder to a sequential, zero-padded numeric
format based on how many files are present, sorted by their current name.

Examples of padding width (based on total file count):
    100 files   -> 001 ... 100      (3 digits)
    1000 files  -> 0001 ... 1000    (4 digits)
    12 files    -> 01 ... 12        (2 digits)

Original file extensions are preserved. The script does a safe two-phase
rename (to temporary names first) so it works correctly even if the final
names collide with existing file names.

Usage:
    python rename_files.py /path/to/folder
    python rename_files.py /path/to/folder --start 1 --dry-run --prefix "IMG_"
    python rename_files.py /path/to/folder --prefix "IMG_"

Options:
    --start N      Number to start counting from (default: 1)
    --prefix TEXT  Optional prefix before the number (default: "")
    --dry-run      Show what would be renamed without actually renaming
"""

import argparse
import os
import sys


def get_files_sorted_by_name(folder):
    """Return a list of file names (not directories) in folder, sorted by name."""
    entries = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
    ]
    entries.sort()
    return entries


def rename_files(folder, start=1, prefix="", dry_run=False):
    files = get_files_sorted_by_name(folder)
    count = len(files)

    if count == 0:
        print("No files found in the folder.")
        return

    # Digit width is based on the highest number that will be used
    highest_number = start + count - 1
    width = max(len(str(highest_number)), len(str(count)))

    print(f"Found {count} file(s). Using {width}-digit numbering "
          f"({str(start).zfill(width)}-{str(highest_number).zfill(width)}).\n")

    # Build the list of (old_name, new_name) pairs
    rename_plan = []
    for i, filename in enumerate(files, start=start):
        _, ext = os.path.splitext(filename)
        new_name = f"{prefix}{str(i).zfill(width)}{ext}"
        rename_plan.append((filename, new_name))

    if dry_run:
        for old, new in rename_plan:
            print(f"[DRY RUN] {old}  ->  {new}")
        print("\nDry run complete. No files were changed.")
        return

    # Phase 1: rename all files to temporary names to avoid collisions
    # (e.g. renaming 1.jpg -> 2.jpg when 2.jpg already exists)
    temp_names = []
    for idx, (old, new) in enumerate(rename_plan):
        old_path = os.path.join(folder, old)
        temp_path = os.path.join(folder, f"__tmp_rename_{idx}__")
        os.rename(old_path, temp_path)
        temp_names.append((temp_path, new))

    # Phase 2: rename temp files to their final names
    for temp_path, new in temp_names:
        new_path = os.path.join(folder, new)
        os.rename(temp_path, new_path)
        print(f"{os.path.basename(temp_path)} -> {new}")

    print(f"\nDone. Renamed {count} file(s).")


def main():
    parser = argparse.ArgumentParser(
        description="Rename files in a folder to sequential zero-padded numbers."
    )
    parser.add_argument("folder", help="Path to the folder containing the files")
    parser.add_argument("--start", type=int, default=1,
                         help="Number to start counting from (default: 1)")
    parser.add_argument("--prefix", type=str, default="",
                         help="Optional prefix before the number (default: none)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Preview the renaming without making changes")

    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"Error: '{args.folder}' is not a valid folder.")
        sys.exit(1)

    rename_files(args.folder, start=args.start, prefix=args.prefix, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
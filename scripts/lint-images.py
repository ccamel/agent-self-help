#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

MAX_BYTES = 500 * 1024
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}

files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
)
errors = []
for filename in files.split(b"\0"):
    if not filename:
        continue
    path = Path(filename.decode(sys.getfilesystemencoding(), errors="surrogateescape"))
    if path.suffix.lower() not in IMAGE_EXTENSIONS or not path.is_file():
        continue
    if path.suffix.lower() == ".png":
        errors.append(f"{path}: PNG is not allowed; use WebP or SVG")
    if path.stat().st_size > MAX_BYTES:
        errors.append(f"{path}: exceeds {MAX_BYTES // 1024} KiB")

if errors:
    sys.exit("\n".join(errors))
print(f"Image lint passed (maximum {MAX_BYTES // 1024} KiB; no PNG)")

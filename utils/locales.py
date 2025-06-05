#!/usr/bin/env python
# encoding: utf-8

import sys
import subprocess

from pathlib import Path

src_dir = Path(__file__).parent.parent / "src"

for po_file in src_dir.glob("bagit/locale/*/LC_MESSAGES/bagit-python.po"):
    mo_file = po_file.with_suffix(".mo")

    if not mo_file.is_file() or mo_file.stat().st_mtime < po_file.stat().st_mtime:
        try:
            print(f"compiling {po_file} to {mo_file}")
            subprocess.check_call(["msgfmt", "-o", mo_file, po_file])
        except (OSError, subprocess.CalledProcessError) as exc:
            print(
                "Translation catalog %s could not be compiled (is gettext installed?) "
                " — translations will not be available for this language: %s"
                % (po_file, exc),
                file=sys.stderr,
            )
            continue

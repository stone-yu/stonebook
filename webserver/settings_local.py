#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
from pathlib import Path


def build_settings(root=None):
    project_root = Path(root or os.environ.get("TALEBOOK_LOCAL_ROOT") or Path(__file__).resolve().parents[1]).resolve()
    code_root = Path(__file__).resolve().parents[1]
    data_root = project_root / "data"

    def directory(path):
        return f"{path}{os.sep}"

    return {
        # calibre-debug cannot be restarted like a normal Python executable:
        # Tornado would lose the required `-e bridge.py --` arguments.
        "autoreload": False,
        # Nuxt keeps reader assets in public/static during development. This
        # also lets the /read proxy follow Tornado's PDF viewer redirect.
        "static_path": directory(code_root / "app" / "public" / "static"),
        "settings_path": directory(data_root / "settings"),
        "progress_path": directory(data_root / "progress"),
        "themes_path": directory(data_root / "themes"),
        "convert_path": directory(data_root / "work" / "convert"),
        "upload_path": directory(data_root / "work" / "upload"),
        "extract_path": directory(data_root / "work" / "extract"),
        "scan_upload_path": directory(project_root / "imports"),
        "with_library": directory(project_root / "library"),
        "user_database": f"sqlite:///{data_root / 'calibre-webserver.db'}",
        "ssl_crt_file": str(data_root / "ssl" / "ssl.crt"),
        "ssl_key_file": str(data_root / "ssl" / "ssl.key"),
        "AUDIOBOOK_PATH": str(project_root / "audiobooks"),
    }


settings = build_settings()

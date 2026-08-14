#!/usr/bin/env python3

"""Bridge Calibre's embedded Python with Talebook's local virtualenv."""

import os
import runpy
import sys
from pathlib import Path


def main():
    # The local root stores mutable data only. Application code always lives
    # beside this bridge script in the checked-out repository.
    project_root = Path(__file__).resolve().parents[1]
    site_packages = Path(os.environ["TALEBOOK_LOCAL_SITE_PACKAGES"]).resolve()
    # Prefer modules bundled with Calibre (notably its binary extensions), then
    # fill in Talebook-only dependencies from the repository virtualenv.
    sys.path.append(str(site_packages))
    sys.path.insert(0, str(project_root))
    sys.argv = [str(project_root / "server.py"), *sys.argv[1:]]
    runpy.run_path(str(project_root / "server.py"), run_name="__main__")


if __name__ == "__main__":
    main()

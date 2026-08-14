#!/usr/bin/env pytest
# -*- coding: UTF-8 -*-

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PERSISTENT_VOLUME = "${TALEBOOK_DATA_DIR:-./data}:/data"
IMPORTS_VOLUME = "${TALEBOOK_IMPORTS_DIR:-./imports}:/imports"
LIBRARY_VOLUME = "${TALEBOOK_LIBRARY_DIR:-./library}:/library"
AUDIOBOOKS_VOLUME = "${TALEBOOK_AUDIOBOOKS_DIR:-./audiobooks}:/audiobooks"


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_production_compose_defaults_to_persistent_local_data_directory():
    compose = yaml.safe_load(read("docker-compose.yml"))
    volumes = compose["services"]["talebook"]["volumes"]

    assert volumes == [PERSISTENT_VOLUME, IMPORTS_VOLUME, LIBRARY_VOLUME, AUDIOBOOKS_VOLUME]
    assert all(not volume.startswith("/tmp/") for volume in volumes)


def test_runtime_uses_flat_storage_roots_and_persistent_calibre_config():
    settings = read("webserver/settings.py")
    assert '"settings_path" : "/data/settings/"' in settings
    assert '"progress_path" : "/data/progress/"' in settings
    assert '"convert_path"  : "/data/work/convert/"' in settings
    assert '"upload_path"   : "/data/work/upload/"' in settings
    assert '"scan_upload_path"   : "/imports/"' in settings
    assert '"extract_path"  : "/data/work/extract/"' in settings
    assert '"with_library"  : "/library/"' in settings
    assert "sqlite:////data/calibre-webserver.db" in settings
    assert '"AUDIOBOOK_PATH": "/audiobooks"' in settings

    dockerfile = read("Dockerfile")
    assert "ENV CALIBRE_CONFIG_DIRECTORY=/data/calibre" in dockerfile
    assert "/root/.config/calibre" not in read("docker/start.sh")
    assert "/root/.config/calibre" not in read("docker/start-dev.sh")


def test_runtime_contract_does_not_reference_legacy_data_books_paths():
    for relative_path in (
        "Dockerfile",
        "conf/supervisor/talebook.conf",
        "conf/supervisor/server-side-render.conf",
        "conf/supervisor/dev.conf",
        "webserver/settings.py",
    ):
        assert "/data/books" not in read(relative_path), relative_path


def test_image_prebuild_keeps_application_state_and_library_separate():
    dockerfile = read("Dockerfile")
    assert "mkdir -p /prebuilt/data /prebuilt/library" in dockerfile
    assert "cp -a /data/. /prebuilt/data/" in dockerfile
    assert "cp -a /library/. /prebuilt/library/" in dockerfile
    assert 'VOLUME ["/data", "/imports", "/library", "/audiobooks"]' in dockerfile

    start = read("docker/start.sh")
    assert "cp /prebuilt/data/calibre-webserver.db /data/" in start
    assert "cp -a /prebuilt/library/. /library/" in start
    assert 'if [ "$legacy_layout" = "0" ]; then' in start


def test_deployment_docs_explain_persistence_and_do_not_recommend_tmp_data():
    for relative_path in ("README.md", "README_EN.md", "CODE_WIKI.md"):
        content = read(relative_path)

        assert "TALEBOOK_DATA_DIR" in content
        assert "TALEBOOK_IMPORTS_DIR" in content
        assert "TALEBOOK_LIBRARY_DIR" in content
        assert "TALEBOOK_AUDIOBOOKS_DIR" in content
        assert PERSISTENT_VOLUME in content or "$PWD/data:/data" in content
        assert "-v /tmp/demo:/data" not in content

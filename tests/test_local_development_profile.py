import importlib.util
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_dev_local():
    spec = importlib.util.spec_from_file_location("dev_local", ROOT / "scripts" / "dev_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_local_backend_bridge():
    spec = importlib.util.spec_from_file_location("run_local_backend", ROOT / "scripts" / "run_local_backend.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_profile_maps_all_mutable_storage_below_the_project_root(tmp_path):
    from webserver.settings_local import build_settings

    settings = build_settings(tmp_path)

    assert settings["settings_path"] == f"{tmp_path}/data/settings/"
    assert settings["progress_path"] == f"{tmp_path}/data/progress/"
    assert settings["convert_path"] == f"{tmp_path}/data/work/convert/"
    assert settings["upload_path"] == f"{tmp_path}/data/work/upload/"
    assert settings["extract_path"] == f"{tmp_path}/data/work/extract/"
    assert settings["scan_upload_path"] == f"{tmp_path}/imports/"
    assert settings["with_library"] == f"{tmp_path}/library/"
    assert settings["user_database"] == f"sqlite:///{tmp_path}/data/calibre-webserver.db"
    assert settings["AUDIOBOOK_PATH"] == f"{tmp_path}/audiobooks"
    assert settings["autoreload"] is False
    assert settings["static_path"] == f"{ROOT}/app/public/static/"


def test_local_env_file_configures_the_data_root_without_shell_prefixes(tmp_path):
    dev_local = load_dev_local()
    (tmp_path / ".env").write_text(
        "# local storage\nexport TALEBOOK_LOCAL_ROOT='storage/talebook'\nIGNORED_KEY=value\n",
        encoding="utf-8",
    )

    env = dev_local.load_local_env(tmp_path, {"PATH": "/usr/bin"})

    assert env["TALEBOOK_LOCAL_ROOT"] == "storage/talebook"
    assert "IGNORED_KEY" not in env
    assert dev_local.resolve_local_root(tmp_path, env) == (tmp_path / "storage" / "talebook").resolve()


def test_process_environment_overrides_the_local_env_file(tmp_path):
    dev_local = load_dev_local()
    (tmp_path / ".env").write_text("TALEBOOK_LOCAL_ROOT=from-file\n", encoding="utf-8")

    env = dev_local.load_local_env(tmp_path, {"TALEBOOK_LOCAL_ROOT": "/from/environment"})

    assert env["TALEBOOK_LOCAL_ROOT"] == "/from/environment"


def test_invalid_local_env_file_reports_the_line_number(tmp_path):
    dev_local = load_dev_local()
    (tmp_path / ".env").write_text("TALEBOOK_LOCAL_ROOT\n", encoding="utf-8")

    with pytest.raises(dev_local.LocalDevelopmentError, match=r"\.env:1"):
        dev_local.load_local_env(tmp_path, {})


def test_default_settings_keep_the_container_storage_contract():
    from webserver.settings import settings

    assert settings["settings_path"] == "/data/settings/"
    assert settings["scan_upload_path"] == "/imports/"
    assert settings["with_library"] == "/library/"
    assert settings["user_database"] == "sqlite:////data/calibre-webserver.db"
    assert settings["AUDIOBOOK_PATH"] == "/audiobooks"


def test_calibre_tool_detection_supports_an_explicit_mac_app_directory(tmp_path):
    dev_local = load_dev_local()
    calibre_bin = tmp_path / "calibre-bin"
    calibre_bin.mkdir()
    for name in ("calibre-debug", "calibredb"):
        (calibre_bin / name).touch()

    tools = dev_local.find_calibre_tools({"TALEBOOK_CALIBRE_BIN_DIR": str(calibre_bin)})

    assert tools == (calibre_bin / "calibre-debug", calibre_bin / "calibredb")


def test_prepare_directories_creates_the_flat_local_layout(tmp_path):
    dev_local = load_dev_local()

    dev_local.prepare_directories(tmp_path)

    for relative_path in dev_local.REQUIRED_LOCAL_DIRS:
        assert (tmp_path / relative_path).is_dir()


def test_scan_path_validation_accepts_local_import_tree(tmp_path):
    from webserver.handlers.scan import scan_path_is_allowed

    imports = tmp_path / "imports"
    nested = imports / "文学" / "book.epub"
    env = {"TALEBOOK_PROFILE": "local", "TALEBOOK_LOCAL_ROOT": str(tmp_path)}

    assert scan_path_is_allowed(imports, env) is True
    assert scan_path_is_allowed(nested, env) is True
    assert scan_path_is_allowed(tmp_path / "library", env) is False


def test_scan_path_validation_keeps_container_boundary():
    from webserver.handlers.scan import scan_path_is_allowed

    assert scan_path_is_allowed("/imports/文学/book.epub", {}) is True
    assert scan_path_is_allowed("/library/book.epub", {}) is False


def test_backend_command_uses_calibre_embedded_python_bridge(tmp_path):
    dev_local = load_dev_local()

    command = dev_local.backend_command(Path("/calibre/calibre-debug"), tmp_path, ["--syncdb"])

    assert command == [
        "/calibre/calibre-debug",
        "-e",
        str(tmp_path / "scripts" / "run_local_backend.py"),
        "--",
        "--syncdb",
    ]


def test_local_backend_bridge_reads_code_from_repository_not_data_root(tmp_path):
    bridge = load_local_backend_bridge()
    data_root = tmp_path / "external-data"
    site_packages = tmp_path / "site-packages"

    with (
        mock.patch.dict(
            os.environ,
            {
                "TALEBOOK_LOCAL_ROOT": str(data_root),
                "TALEBOOK_LOCAL_SITE_PACKAGES": str(site_packages),
            },
        ),
        mock.patch.object(bridge.runpy, "run_path") as run_path,
        mock.patch.object(bridge.sys, "argv", ["bridge", "--syncdb"]),
        mock.patch.object(bridge.sys, "path", []),
    ):
        bridge.main()

    assert run_path.call_args.args[0] == str(ROOT / "server.py")
    assert run_path.call_args.kwargs == {"run_name": "__main__"}


def test_calibre_runtime_rejects_a_virtualenv_python_version_mismatch(tmp_path):
    dev_local = load_dev_local()
    version = subprocess.CompletedProcess([], 0, stdout="3.12\n")

    with mock.patch.object(subprocess, "run", return_value=version):
        with pytest.raises(dev_local.LocalDevelopmentError, match="Calibre 使用 Python 3.12"):
            dev_local.check_calibre_runtime(Path("calibre-debug"), tmp_path, (3, 11))


def test_calibre_runtime_checks_project_dependencies_inside_embedded_python(tmp_path):
    dev_local = load_dev_local()
    version = subprocess.CompletedProcess([], 0, stdout="3.11\n")

    with mock.patch.object(subprocess, "run", side_effect=[version, subprocess.CompletedProcess([], 0)]) as run:
        dev_local.check_calibre_runtime(Path("calibre-debug"), tmp_path, (3, 11))

    dependency_command = run.call_args_list[1].args[0]
    assert dependency_command[:2] == ["calibre-debug", "-c"]
    assert "sys.path.append" in dependency_command[2]
    assert "sqlalchemy" in dependency_command[2]


def test_initialize_is_idempotent_when_databases_exist(tmp_path):
    dev_local = load_dev_local()
    dev_local.prepare_directories(tmp_path)
    (tmp_path / "library" / "metadata.db").touch()
    (tmp_path / "data" / "calibre-webserver.db").touch()

    with mock.patch.object(subprocess, "run") as run:
        dev_local.initialize(Path("calibre-debug"), Path("calibredb"), tmp_path / "site-packages", tmp_path)

    run.assert_called_once()
    assert run.call_args.args[0][-1] == "--syncdb"
    assert (tmp_path / "data" / "settings" / "auto.py").is_file()


def test_initialize_reads_preset_books_from_code_root_and_writes_to_configured_root(tmp_path):
    dev_local = load_dev_local()
    code_root = tmp_path / "code"
    local_root = tmp_path / "storage"
    dev_local.prepare_directories(local_root)
    (code_root / "docker" / "book").mkdir(parents=True)
    (local_root / "data" / "calibre-webserver.db").touch()

    with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
        dev_local.initialize(Path("calibre-debug"), Path("calibredb"), tmp_path / "site", code_root, local_root)

    assert run.call_count == 2
    command = run.call_args_list[0].args[0]
    assert f"--library-path={local_root / 'library'}" in command
    assert command[-1] == str(code_root / "docker" / "book")
    assert run.call_args_list[1].args[0][-1] == "--syncdb"


def test_local_environment_does_not_reuse_the_user_calibre_configuration(tmp_path):
    dev_local = load_dev_local()

    env = dev_local.local_environment(tmp_path / "site-packages", tmp_path, {"PATH": os.environ["PATH"]})

    assert env["TALEBOOK_PROFILE"] == "local"
    assert env["TALEBOOK_LOCAL_ROOT"] == str(tmp_path)
    assert env["CALIBRE_CONFIG_DIRECTORY"] == str(tmp_path / "data" / "calibre")

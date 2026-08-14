#!/usr/bin/env python3

"""Prepare and run Talebook locally with Calibre's embedded Python."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MACOS_CALIBRE_BIN = Path("/Applications/calibre.app/Contents/MacOS")
REQUIRED_LOCAL_DIRS = (
    "data/settings",
    "data/progress",
    "data/themes",
    "data/logo",
    "data/ssl",
    "data/calibre",
    "data/work/upload",
    "data/work/convert",
    "data/work/extract",
    "imports",
    "library",
    "audiobooks",
)
LOCAL_ENV_KEYS = {"TALEBOOK_LOCAL_ROOT", "TALEBOOK_CALIBRE_BIN_DIR"}


class LocalDevelopmentError(RuntimeError):
    pass


def load_local_env(project_root=PROJECT_ROOT, environ=None):
    env = dict(os.environ if environ is None else environ)
    env_file = project_root / ".env"
    if not env_file.is_file():
        return env

    for line_number, raw_line in enumerate(env_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise LocalDevelopmentError(f"{env_file}:{line_number} 不是有效的 KEY=value 配置")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in LOCAL_ENV_KEYS or key in env:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if not value:
            raise LocalDevelopmentError(f"{env_file}:{line_number} 的 {key} 不能为空")
        env[key] = value
    return env


def resolve_local_root(project_root=PROJECT_ROOT, environ=None):
    environ = os.environ if environ is None else environ
    configured = environ.get("TALEBOOK_LOCAL_ROOT")
    if not configured:
        return project_root.resolve()
    root = Path(configured).expanduser()
    if not root.is_absolute():
        root = project_root / root
    return root.resolve()


def find_calibre_tools(environ=None):
    environ = os.environ if environ is None else environ
    override = environ.get("TALEBOOK_CALIBRE_BIN_DIR")
    candidates = [Path(override).expanduser()] if override else []
    candidates.append(MACOS_CALIBRE_BIN)

    path_debug = shutil.which("calibre-debug")
    if path_debug:
        candidates.append(Path(path_debug).resolve().parent)

    for directory in candidates:
        calibre_debug = directory / "calibre-debug"
        calibredb = directory / "calibredb"
        if calibre_debug.is_file() and calibredb.is_file():
            return calibre_debug, calibredb

    raise LocalDevelopmentError(
        "找不到 calibre-debug 和 calibredb。请先执行 `brew install --cask calibre`，或设置 TALEBOOK_CALIBRE_BIN_DIR。"
    )


def find_site_packages(project_root=PROJECT_ROOT):
    python = project_root / ".venv" / "bin" / "python"
    if not python.is_file():
        raise LocalDevelopmentError(
            "找不到 .venv。请先执行 `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`。"
        )
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import json,sys,sysconfig; print(json.dumps({'site': sysconfig.get_paths()['purelib'], "
            "'version': list(sys.version_info[:2])}))",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    details = json.loads(result.stdout)
    site_packages = Path(details["site"])
    if not site_packages.is_dir():
        raise LocalDevelopmentError(f"虚拟环境 site-packages 不存在：{site_packages}")
    return site_packages, tuple(details["version"])


def check_calibre_runtime(calibre_debug, site_packages, venv_version):
    version_result = subprocess.run(
        [str(calibre_debug), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
        check=True,
        capture_output=True,
        text=True,
    )
    calibre_version = tuple(int(part) for part in version_result.stdout.strip().split("."))
    if calibre_version != venv_version:
        expected = ".".join(str(part) for part in calibre_version)
        actual = ".".join(str(part) for part in venv_version)
        raise LocalDevelopmentError(
            f"Calibre 使用 Python {expected}，但 .venv 使用 Python {actual}。请用 Python {expected} 重新创建 .venv。"
        )

    dependency_check = (
        "import sys; "
        f"sys.path.append({str(site_packages)!r}); "
        "import bcrypt,jinja2,lxml,psutil,quickjs,social_core,sqlalchemy,tornado"
    )
    subprocess.run([str(calibre_debug), "-c", dependency_check], check=True)


def prepare_directories(project_root=PROJECT_ROOT):
    for relative_path in REQUIRED_LOCAL_DIRS:
        (project_root / relative_path).mkdir(parents=True, exist_ok=True)


def local_environment(site_packages, local_root=PROJECT_ROOT, environ=None):
    env = dict(os.environ if environ is None else environ)
    env.update(
        {
            "TALEBOOK_PROFILE": "local",
            "TALEBOOK_LOCAL_ROOT": str(local_root),
            "TALEBOOK_LOCAL_SITE_PACKAGES": str(site_packages),
            "CALIBRE_CONFIG_DIRECTORY": str(local_root / "data" / "calibre"),
        }
    )
    return env


def backend_command(calibre_debug, project_root=PROJECT_ROOT, extra_args=None):
    return [
        str(calibre_debug),
        "-e",
        str(project_root / "scripts" / "run_local_backend.py"),
        "--",
        *(extra_args or []),
    ]


def initialize(calibre_debug, calibredb, site_packages, project_root=PROJECT_ROOT, local_root=None):
    local_root = Path(local_root or project_root)
    env = local_environment(site_packages, local_root)
    library = local_root / "library"
    if not (library / "metadata.db").exists():
        subprocess.run(
            [str(calibredb), "add", f"--library-path={library}", "--recurse", str(project_root / "docker" / "book")],
            check=True,
            env=env,
        )

    database = local_root / "data" / "calibre-webserver.db"
    if not database.exists():
        subprocess.run(backend_command(calibre_debug, project_root, ["--syncdb"]), check=True, env=env)

    auto_settings = local_root / "data" / "settings" / "auto.py"
    auto_settings.touch(exist_ok=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查环境并准备本地目录")
    parser.add_argument("--init-only", action="store_true", help="初始化数据库和书库后退出")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        runtime_env = load_local_env()
        local_root = resolve_local_root(environ=runtime_env)
        calibre_debug, calibredb = find_calibre_tools(runtime_env)
        site_packages, venv_version = find_site_packages()
        prepare_directories(local_root)
        check_calibre_runtime(calibre_debug, site_packages, venv_version)
        print(f"Calibre: {calibre_debug.parent}")
        print(f"Python dependencies: {site_packages}")
        print(f"Local root: {local_root}")
        if args.check:
            return 0
        initialize(calibre_debug, calibredb, site_packages, PROJECT_ROOT, local_root)
        if args.init_only:
            return 0
        env = local_environment(site_packages, local_root, runtime_env)
        command = backend_command(calibre_debug, extra_args=["--host=127.0.0.1", "--port=8080"])
        return subprocess.run(command, env=env, check=False).returncode
    except (LocalDevelopmentError, subprocess.CalledProcessError) as error:
        print(f"本地开发环境启动失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

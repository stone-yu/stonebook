import logging
from types import SimpleNamespace
from unittest import mock

from webserver.handlers.base import BaseHandler
from webserver.loader import normalize_header_brand, normalize_site_title
from webserver.logging_config import configure_logging, resolve_log_file


def test_legacy_default_brand_is_normalized_without_touching_custom_titles():
    assert normalize_site_title("TaleBook") == "StoneBook"
    assert normalize_site_title("My TaleBook") == "My TaleBook"
    assert "StoneBook" in normalize_header_brand("给 talebook 点击一个Star")


def test_resolve_log_file_uses_data_directory_for_local_profile(tmp_path):
    settings_path = tmp_path / "data" / "settings"
    resolved = resolve_log_file({"settings_path": str(settings_path)}, SimpleNamespace(log_file_prefix=None))

    assert resolved == str(tmp_path / "data" / "log" / "talebook.log")


def test_resolve_log_file_keeps_explicit_tornado_path(tmp_path):
    explicit = tmp_path / "custom.log"

    assert resolve_log_file({}, SimpleNamespace(log_file_prefix=str(explicit))) == str(explicit)


def test_configure_logging_adds_console_and_file_once(tmp_path):
    root = logging.Logger("stonebook-test")
    settings = {"settings_path": str(tmp_path / "data" / "settings")}
    options = SimpleNamespace(log_file_prefix=None)

    with mock.patch("webserver.logging_config.logging.getLogger", return_value=root):
        log_file = configure_logging(settings, options)
        configure_logging(settings, options)
        root.info("[STARTUP] StoneBook test")

    try:
        assert log_file == str(tmp_path / "data" / "log" / "talebook.log")
        assert len([item for item in root.handlers if isinstance(item, logging.FileHandler)]) == 1
        assert (
            len(
                [
                    item
                    for item in root.handlers
                    if isinstance(item, logging.StreamHandler) and not isinstance(item, logging.FileHandler)
                ]
            )
            == 1
        )
        for handler in root.handlers:
            handler.flush()
        assert "[STARTUP] StoneBook test" in (tmp_path / "data" / "log" / "talebook.log").read_text()
    finally:
        for handler in root.handlers:
            handler.close()


def test_write_request_audit_excludes_query_and_body():
    handler = SimpleNamespace(
        request=SimpleNamespace(method="POST", path="/api/admin/settings", remote_ip="127.0.0.1"),
        _request_started_at=10.0,
        user_id=lambda: 7,
        get_status=lambda: 200,
        session=SimpleNamespace(close=mock.Mock()),
    )

    with (
        mock.patch("webserver.handlers.base.time.monotonic", return_value=10.025),
        mock.patch("webserver.handlers.base.logging.info") as log_info,
    ):
        BaseHandler.on_finish(handler)

    log_info.assert_called_once_with(
        "[AUDIT] method=%s path=%s status=%s user_id=%s ip=%s duration_ms=%s",
        "POST",
        "/api/admin/settings",
        200,
        7,
        "127.0.0.1",
        25,
    )
    handler.session.close.assert_called_once_with()

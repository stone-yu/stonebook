#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging
import logging.handlers
import os

import tornado.log


LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def resolve_log_file(settings, tornado_options=None):
    """Return the same persistent application log path for runtime and admin UI."""
    configured = getattr(tornado_options, "log_file_prefix", None) if tornado_options is not None else None
    if configured:
        return os.path.abspath(os.path.expanduser(configured))

    settings_path = os.path.abspath(os.path.expanduser(settings.get("settings_path", "/data/settings/")))
    data_path = os.path.dirname(settings_path.rstrip(os.sep))
    return os.path.join(data_path, "log", "talebook.log")


def configure_logging(settings, tornado_options=None):
    """Ensure INFO logs reach both stderr and the persistent system log."""
    root = logging.getLogger()
    root.setLevel(min(root.level, logging.INFO) if root.level else logging.INFO)
    formatter = tornado.log.LogFormatter()

    has_console = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in root.handlers
    )
    if not has_console:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        root.addHandler(console)

    log_file = resolve_log_file(settings, tornado_options)
    has_file = any(
        isinstance(handler, logging.FileHandler) and os.path.abspath(getattr(handler, "baseFilename", "")) == log_file
        for handler in root.handlers
    )
    if not has_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return log_file

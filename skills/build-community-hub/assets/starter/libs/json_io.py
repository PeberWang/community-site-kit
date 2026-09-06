# -*- coding: utf-8 -*-
"""Locked, atomic UTF-8 JSON and text I/O."""

import fcntl
import json
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from libs.exceptions import StoreException

_thread_lock_guard = threading.Lock()
_thread_locks = {}


@contextmanager
def path_lock(path: Path, exclusive: bool = False) -> Iterator[None]:
    """Use a sibling lock file so independent web/script processes coordinate."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    with _thread_lock_guard:
        thread_lock = _thread_locks.setdefault(str(lock_path), threading.RLock())
    with thread_lock:
        with open(lock_path, "a+", encoding="utf-8", newline="\n") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def read_json_unlocked(path: Path, default: Any) -> Any:
    if not Path(path).exists():
        return default
    try:
        with open(path, "r", encoding="utf-8", newline="\n") as source:
            return json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StoreException(f"无法读取数据文件 {path}: {error}") from error


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temporary, "w", encoding="utf-8", newline="\n") as target:
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise StoreException(f"无法写入数据文件 {path}: {error}") from error


def write_json_unlocked(path: Path, obj: Any) -> None:
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temporary, "w", encoding="utf-8", newline="\n") as target:
            json.dump(obj, target, ensure_ascii=False, indent=2)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise StoreException(f"无法写入数据文件 {path}: {error}") from error


def read_json(path: Path, default: Any) -> Any:
    with path_lock(path):
        return read_json_unlocked(path, default)


def write_json(path: Path, obj: Any) -> None:
    with path_lock(path, exclusive=True):
        write_json_unlocked(path, obj)

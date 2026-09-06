# -*- coding: utf-8 -*-
"""Typed JSON stores - one file per entity kind under data/db/.

Each store keeps a list of pydantic models; callers get/put whole records.
Heavy payloads never live here (OSS only); only metadata + pointers.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Type

from pydantic import BaseModel

from libs.json_io import path_lock, read_json, read_json_unlocked, write_json_unlocked


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class JsonStore:
    """Generic store: data/db/<name>.json <-> list of pydantic models."""

    def __init__(self, db_dir: Path, name: str, model: Type[BaseModel],
                 key: Callable[[BaseModel], str]):
        self.path = Path(db_dir) / f"{name}.json"
        self.model = model
        self.key = key

    def all(self) -> List[BaseModel]:
        raw = read_json(self.path, [])
        return [self.model.model_validate(r) for r in raw]

    def _all_unlocked(self) -> List[BaseModel]:
        raw = read_json_unlocked(self.path, [])
        return [self.model.model_validate(r) for r in raw]

    def _dump_unlocked(self, items: List[BaseModel]) -> None:
        write_json_unlocked(self.path, [i.model_dump() for i in items])

    def get(self, key_value: str) -> Optional[BaseModel]:
        for item in self.all():
            if self.key(item) == key_value:
                return item
        return None

    def put(self, item: BaseModel) -> BaseModel:
        """Insert or replace by key."""
        with path_lock(self.path, exclusive=True):
            items = self._all_unlocked()
            for idx, existing in enumerate(items):
                if self.key(existing) == self.key(item):
                    items[idx] = item
                    self._dump_unlocked(items)
                    return item
            items.append(item)
            self._dump_unlocked(items)
            return item

    def delete(self, key_value: str) -> bool:
        with path_lock(self.path, exclusive=True):
            items = self._all_unlocked()
            kept = [i for i in items if self.key(i) != key_value]
            if len(kept) == len(items):
                return False
            self._dump_unlocked(kept)
            return True

    def find(self, pred: Callable[[BaseModel], bool]) -> List[BaseModel]:
        return [i for i in self.all() if pred(i)]

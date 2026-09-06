# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import BaseModel

from libs.exceptions import StoreException
from services.store import JsonStore


class Entry(BaseModel):
    id: str
    value: int


def test_concurrent_puts_keep_every_record(tmp_path):
    store = JsonStore(tmp_path, "entries", Entry, key=lambda entry: entry.id)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda number: store.put(Entry(id=str(number), value=number)), range(100)))

    saved = {entry.id for entry in store.all()}
    assert saved == {str(number) for number in range(100)}


def test_corrupt_json_fails_closed(tmp_path):
    path = tmp_path / "entries.json"
    path.write_text("{not json", encoding="utf-8", newline="\n")
    store = JsonStore(tmp_path, "entries", Entry, key=lambda entry: entry.id)

    with pytest.raises(StoreException):
        store.put(Entry(id="1", value=1))

    assert path.read_text(encoding="utf-8") == "{not json"

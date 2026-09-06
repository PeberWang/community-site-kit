import json
from pathlib import Path

from libs.community_config import load_community


def test_bundled_community_config_is_valid():
    load_community.cache_clear()
    config = load_community("config/community.json")
    assert config.site.name
    assert config.features.home is True


def test_custom_module_switches(tmp_path):
    with Path("config/community.json").open("r", encoding="utf-8", newline="\n") as handle:
        source = json.load(handle)
    source["features"]["plaza"] = True
    path = tmp_path / "community.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8", newline="\n")
    load_community.cache_clear()
    assert load_community(str(path)).features.plaza is True

# -*- coding: utf-8 -*-
"""Load public community configuration from JSON."""

import json
from functools import lru_cache
from pathlib import Path

from config.community_schema import CommunityConfig


@lru_cache(maxsize=4)
def load_community(path: str) -> CommunityConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8", newline="\n") as handle:
        return CommunityConfig.model_validate(json.load(handle))

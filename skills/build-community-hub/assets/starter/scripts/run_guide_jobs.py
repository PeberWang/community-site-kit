#!/usr/bin/env python3
"""Prepare due guide candidates. This script never publishes a guide."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from glue.guide_lifecycle import GuideLifecycle


async def main() -> None:
    completed = await GuideLifecycle(settings).process_due_jobs()
    print(f"prepared_candidates={completed}")


if __name__ == "__main__":
    asyncio.run(main())

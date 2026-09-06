#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Knowledge Common Kit web entry point: python run.py."""

import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.main import run

if __name__ == "__main__":
    run()

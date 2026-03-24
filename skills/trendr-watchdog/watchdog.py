#!/usr/bin/env python3
"""Compatibility entrypoint for older TrendR launch commands."""

from supervisor import main


if __name__ == "__main__":
    raise SystemExit(main())

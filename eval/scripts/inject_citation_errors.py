#!/usr/bin/env python3
"""Inject controlled citation errors into a review markdown file."""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

CITE_PATTERN = re.compile(r"\\cite\{([^}]+)\}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject citation-key corruption for verifier recall tests")
    parser.add_argument("--input", required=True, help="Input review.md")
    parser.add_argument("--output", required=True, help="Output corrupted markdown")
    parser.add_argument("--count", type=int, default=3, help="Number of citation groups to corrupt")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    src = Path(args.input)
    dst = Path(args.output)
    text = src.read_text(encoding="utf-8")

    matches = list(CITE_PATTERN.finditer(text))
    if not matches:
        raise SystemExit("No \\cite{} found in input")

    selected = random.sample(matches, k=min(args.count, len(matches)))
    updated = text
    offset = 0
    for m in selected:
        original_keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        corrupted_keys = [f"fake_{k}" for k in original_keys]
        replacement = "\\cite{" + ",".join(corrupted_keys) + "}"
        start, end = m.span()
        start += offset
        end += offset
        updated = updated[:start] + replacement + updated[end:]
        offset += len(replacement) - (end - start)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()

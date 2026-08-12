#!/usr/bin/env python3
"""Internal control 1: one stateless Kimi candidate and no feedback."""

from ablation0_runner import run_ablation


if __name__ == "__main__":
    raise SystemExit(run_ablation("direct"))

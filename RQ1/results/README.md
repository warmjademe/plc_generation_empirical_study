# RQ1 frozen 100-task result logs

This directory contains the compact, system-generated records used for RQ1. It
contains only runs over the frozen 100-task benchmark. Earlier 30-task and
50-task pilots, aborted launches, candidate workspaces, compiler caches, and
validator build products are intentionally excluded.

## Included records

- `final/baselines/huashuo/`: LLM4PLC-adapted,
  Agents4PLC-reimplemented, and ChatDev-adapted under four models.
- `final/baselines/nas/`: the model-fixed Claude Code and Codex controls.
- `final/proposed_method/nas/`: the proposed method under the same four model
  families used by the PLC-agent comparisons.
- `system_logs/`: small controller logs showing launch and completion state.
- `artifact_manifest.json`: hashes, sizes, host provenance, and protocol status
  for every included summary.
- `derived/`: tables regenerated from the task-level summaries.

Each JSON summary contains one record per benchmark task, including the terminal
status, verified-success flag, candidates consumed, winning attempt when one
exists, usage counters exposed by the provider, and protocol-audit flags. The
large remote run directories remain on the experiment hosts; they exceed 25 GB
because each attempt retains an isolated workspace and validator artifacts.

## Rebuild the tables

Run:

```bash
python3 results/summarize_rq1.py
```

The script fails closed unless all 18 summaries contain exactly the same 100
unique task identifiers. It produces:

- `run_overview.csv`: success rate, candidate cost, and protocol status by
  method and model;
- `verified_success_at_k.csv`: cumulative task-level success for budgets 1--10;
- `cochran_q.csv`: all-100-task omnibus comparisons for the proposed method and
  the three PLC-agent workflows;
- `pairwise_primary.csv`: paired risk differences, deterministic paired-bootstrap
  intervals, exact McNemar tests, and BH--FDR-adjusted p-values.

All RQ1 success rates and paired tests use the fixed denominator of 100 tasks.
Tasks that do not pass the complete Oracle are counted as unsuccessful without
separating failure causes. Runs with `protocol_ok=false` remain available for
audit but are descriptive rather than confirmatory evidence.

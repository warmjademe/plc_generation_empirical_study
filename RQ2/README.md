# RQ2: two-component ablation

RQ2 evaluates only the two components claimed by the method:

- `M01_without_component_1`: removes the requirement-aligned evidence state,
  non-regression anchor, failure memory, and adaptive same-epoch action. It uses
  the latest candidate plus bounded latest raw visible diagnostics as the
  minimal runnable repair loop. Component 2 remains enabled.
- `M10_without_component_2`: preserves the complete component-1 loop, but a
  sealed failure or a persistent mandatory-verifier inconclusive result is
  terminal. No cross-epoch blind restart is allowed.

There is no `M00` joint ablation. The full-method DeepSeek-V4-Flash run from
RQ1 is the paired control. Every arm uses the same Balanced-100 tasks, maximum
of ten candidates, response contract, model identifier, and MatIEC -> PLCverif
-> visible OpenPLC -> sealed OpenPLC judges.

`run_huashuo_deepseek_rq2.sh` launches M01 and M10 concurrently on huashuo.
The authoritative per-task artifacts remain under `our_method/runs` while the
experiment is active. After completion, the compact raw export in this folder
retains model requests/responses, extracted candidates, gate evaluations,
sealed evaluations, result records, and hash-chained ledgers; verbose backend
working files and tool binaries are excluded from GitHub.

## Frozen result

The 2026-08-13 run completed all 100 tasks per arm.  The full RQ1 control,
M01, and M10 verified 70, 37, and 51 tasks, respectively.  On complete paired
cases, deleting component 1 reduced success by 25.6 percentage points (95%
task-bootstrap CI 14.1--37.2; BH-adjusted exact McNemar p=0.000176).  Deleting
component 2 changed success by 2.8 points (95% CI -8.3--13.9; adjusted p=0.804),
so this run does not establish an overall success-rate effect for component 2.
The latter comparison has 27 M10 verifier-inconclusive outcomes; its
infrastructure-extreme difference spans -8 to 21 points.

`results/raw/raw_export_20260813_v1` contains the compact raw requests,
responses, candidates, gate evaluations, sealed evaluations, task results, and
hash-chained ledger events.  `results/derived` contains the paired analysis.

# RQ4: candidate-budget efficiency

RQ4 asks how the verified success rate and resource cost of the full method
change as the candidate-opportunity budget increases.  It uses only the frozen
DeepSeek-V4-Flash Balanced-100 run from RQ1 and makes no new model or validator
calls.

The analyzer truncates every immutable K=10 trajectory at
`K = {1, 3, 5, 7, 10}`.  For each prefix it reports verified success, observed
infrastructure uncertainty, candidate count, API token vector, dated API-cost
estimate, and the sum of validator gate durations.  It also reconstructs the
identifiable terminal-truncation sensitivity for `E_max = {1, 2, 3}` sealed
queries and `R_max = {0, 1}` inconclusive recoveries.

These points are paired prefixes of one stochastic run, not independent model
reruns.  Validator duration is summed work rather than parallel batch
wall-clock time.  The USD estimate uses the DeepSeek-V4-Flash tariff snapshot
published at <https://api-docs.deepseek.com/quick_start/pricing> on 2026-08-13;
the token vector is retained so future readers can recompute cost under another
tariff.

Run on NAS:

```bash
bash RQ4/run_nas_deepseek_rq4.sh
```

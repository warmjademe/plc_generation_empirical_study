# RQ4: candidate-budget efficiency

RQ4 asks how the verified success rate and resource cost of the full method
change as the candidate-opportunity budget increases.  It reuses the frozen
Balanced-100 runs for DeepSeek-V4-Flash, GPT-5.6 Luna,
Gemini-3.5-Flash-Lite, and Claude Sonnet 5 from RQ1 and makes no new model or
validator calls.

The analyzer truncates every immutable K=10 trajectory at
`K = {1, 3, 5, 7, 10}`.  For each prefix it reports verified success, observed
infrastructure uncertainty, candidate count, API token vector, dated API-cost
estimate, and the sum of validator gate durations.  It also reconstructs the
identifiable terminal-truncation sensitivity for `E_max = {1, 2, 3}` sealed
queries and `R_max = {0, 1}` inconclusive recoveries.

These points are paired prefixes of one stochastic run, not independent model
reruns.  Validator duration is summed work rather than parallel batch
wall-clock time.  The cross-model analysis reports token vectors rather than
applying one provider's tariff to every model.  The earlier DeepSeek-only
result retains its dated USD estimate for reproducibility.

Run on NAS:

```bash
bash RQ4/run_nas_all_models_rq4.sh
```

# Internal controls and ablations

The primary comparison uses the same task package, Kimi snapshot, candidate response
contract, maximum output length, and deterministic MatIEC -> PLCverif -> OpenPLC
judges for every method. A complete model response consumes one candidate slot.

| Entry point | Method | Candidate budget | Feedback and state |
|---|---|---:|---|
| `ablation1_direct_at1.py` | Direct@1 | 1 | No feedback; one stateless request |
| `ablation2_independent_at10.py` | Independent@10 | 10 | No feedback; every request is stateless and independent |
| `ablation3_latest_raw_repair_at10.py` | LatestRawRepair@10 | 10 | Latest candidate plus bounded latest MatIEC/PLCverif diagnostics; fixed `PATCH` policy |

`Independent@10` controls for the benefit of merely spending ten candidate
opportunities. `LatestRawRepair@10` is the strongest primary baseline because it
controls for access to compiler and verifier feedback while excluding the proposed
requirement-aligned ledger, non-regression anchor, adaptive repair mode, and
cross-oracle evidence classification. `Direct@1` is a model-capability lower bound;
it does not have the same candidate budget and must not be the sole primary
comparison.

The 2026 Agents4PLC manuscript compares against LLM4PLC and ChatDev. Its public
repository explicitly states that the complete Agents4PLC multi-agent implementation
is unavailable. It also reports a 23-task protocol and thresholded metrics that are
not equivalent to full MatIEC -> PLCverif -> OpenPLC success. Therefore, this package
does not label a newly written approximation as an exact Agents4PLC reproduction.
The reproducible mechanism closest to its compiler/verifier debugging loop is
`LatestRawRepair@10`. These are internal controls, not substitutes for the external
LLM4PLC, Agents4PLC, and ChatDev comparisons. An exact external comparison should be added only if the
authors release the frozen prompts, retrieval corpus, agent workflow, and stopping
rules.

Example (after the final qualified 50-task package is frozen):

```bash
export KIMI_API_KEY='read from the private environment file'
python3 ablation2_independent_at10.py \
  --dataset-root /path/to/final_50_tasks \
  --qualification /path/to/qualification.json \
  --output /path/to/runs/ablation2_kimi_k3 \
  --workers 2
```

The runner refuses unqualified tasks, changed run specifications, incomplete run
directories that could cause duplicate model calls, development-only validators,
model fallback, and any validator order other than MatIEC -> PLCverif -> OpenPLC.
It stores a hash-bound run specification, per-attempt requests and candidates,
validator artifacts, a hash-chained evidence ledger, and a cumulative
VerifiedSuccess@1..10 summary.

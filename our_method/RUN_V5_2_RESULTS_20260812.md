# DeepSeek Agentic Context v5.2 development results

## Protocol and integrity checks

The run used `deepseek-v4-flash` through the official DeepSeek endpoint and the
frozen `datasets_50` manifest. Each task had at most ten generated candidates.
The mandatory judge order was MatIEC, PLCverif over all authored properties,
visible OpenPLC tests, and sealed OpenPLC tests. The exact configuration SHA-256
was `434026ea91648573a7ee3b1f6621ad9300d43526a6b541bab9f752d2c97b8405`.

Before model calls, all 50 reference programs passed the same validation chain.
The final batch contains 50 results. All hash-chained ledgers, model identities,
sealed-query counts, and inconclusive-restart counts passed the batch integrity
checks. These are development results because the current tasks informed method
changes.

## Primary result

Agentic Context v5.2 verified 28 of 50 tasks (56.0%). The terminal states were:

- 28 `verified_success`;
- 19 `candidate_budget_exhausted`;
- 2 `infrastructure_error` after bounded PLCverif recovery;
- 1 `sealed_failure` after the prespecified sealed-query budget.

Verified success at candidate budget k was 5, 10, 17, 18, 22, 25, 28, 28,
28, and 28 for k=1 through k=10. The run used 300 candidates and 2,038,511
tokens, including 1,581,928 prompt tokens and 456,583 completion tokens.

## Paired comparison with v4

On the unchanged 50 task files, v4 verified 24 tasks (48.0%) and v5.2 verified
28 (56.0%), an 8 percentage-point raw difference. The paired outcomes were 17
successes shared by both methods, 11 v5.2-only successes, 7 v4-only successes,
and 15 failures shared by both. A two-sided exact McNemar test on the 18
discordant tasks gives p=0.481; the observed raw difference is therefore not
statistically resolved by this single development run.

The additional successes also required more resources. v4 used 213 candidates
and 1,385,561 tokens; v5.2 used 300 candidates (+40.8%) and 2,038,511 tokens
(+47.1%). Accordingly, the current evidence does not support an information-
efficiency improvement.

Per-category verified successes out of five were:

| Category | v4 | v5.2 |
|---|---:|---:|
| C01 | 4 | 5 |
| C02 | 3 | 5 |
| C03 | 1 | 0 |
| C04 | 4 | 4 |
| C05 | 2 | 4 |
| C06 | 2 | 5 |
| C07 | 2 | 0 |
| C08 | 3 | 3 |
| C09 | 3 | 2 |
| C10 | 0 | 0 |

## Data-quality sensitivity analysis

`C06_M02_bounded_up_down_counter` contains test vectors outside its public
positive-capacity assumption. Excluding this invalid task gives 27/49 for v5.2
and 24/49 for v4.

Three further tasks have documented contract/Oracle ambiguity:
`C02_B08_composite`, `C02_B12_composite`, and `C06_W03_lean_composite`.
Excluding the invalid task and these three ambiguous tasks gives 24/46 (52.2%)
for both v4 and v5.2. The corrected paired table is 17 shared successes, 7
v5.2-only successes, 7 v4-only successes, and 15 shared failures. Thus all four
tasks responsible for the raw net gain are currently non-scoreable. The 56.0%
raw result must not be presented as evidence of improved generalization until a
corrected manifest is frozen and every method is rerun.

## Mechanism observations

Seven tasks used more than one sealed OpenPLC query; four eventually succeeded.
After removing the invalid and ambiguous tasks, two valid successes
(`C09_B04_composite` and `C09_B14_composite`) demonstrate that a blind sealed
restart can recover candidates without exposing hidden traces to the model.

The bounded-state resource profile triggered on five tasks:
`C09_B06_composite`, `C09_B10_composite`, `C10_B02_composite`,
`C10_B03_composite`, and `C10_B04_composite`. None ended in verified success.
The mechanism prevented an inconclusive result from being counted as a pass and
removed the redundant same-candidate retry, but this run supplies no evidence
that it improves functional success.

The C03 and C07 categories regressed, while C01 and C05 improved. Failure review
also showed that a sealed-blind restart discards useful public failure history
from the prior epoch. Preserving a bounded, program-free summary of only public
validator evidence across epochs is a candidate ablation for a future method;
it should be evaluated on a newly frozen holdout rather than tuned repeatedly on
these 50 tasks.

## External baseline context

On the same raw task files, the DeepSeek baseline runs verified 7/50 for the
LLM4PLC workflow adaptation, 13/50 for the Agents4PLC paper reimplementation,
and 7/50 for the ChatDev workflow adaptation. After excluding the four
non-scoreable tasks, these become 6/46, 12/46, and 7/46, respectively. v5.2 is
24/46 on that sensitivity set. These comparisons are development evidence:
the full upstream Agents4PLC implementation is not public, and all three
baselines are workflow adaptations to the common judges rather than claims of
bit-for-bit upstream equivalence.

## Artifact locations

- NAS v5.2 run: `runs/egbs_deepseek_v4_flash_agentic_context_v5_2_datasets50_20260812`
- NAS v5.2 calibration: `runs/calibration_agentic_context_v5_2_full50_20260812`
- v5.2 configuration: `configs/deepseek_v4_flash_agentic_context_v5_2.json`
- v5.2 method description: `METHOD_V5_2.md`
- data-quality findings: `DATA_QUALITY_FINDINGS_20260812.md`

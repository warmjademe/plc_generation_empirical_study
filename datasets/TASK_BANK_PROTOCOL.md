# 200-Task Bank and Kimi-K3 Failure-50 Selection Protocol

## Purpose

The 200-task bank is a pre-screening candidate pool, not the final benchmark.
It supports a model-conditioned challenge-set construction experiment: run one
isolated Kimi-K3 generation on every frozen task, then retain five genuine
semantic failures from each of ten PLC-behavior categories. The resulting set
is a Kimi-K3-conditioned failure set; it must not be presented as an unbiased sample
of all IEC 61131-3 programs or as an unbiased estimate of Kimi-K3 accuracy.

## Task construction

The source dataset defines five independently specified behaviors in each of ten
categories. Within each category, all ordered pairs A-to-B with A different from
B produce 20 tasks, for 200 tasks in total. A task contains both source behaviors
and a directional supervisory contract: an observed output from A latches
`CrossReady`, `CrossReset` has priority, B executes only when enabled and ready,
isolated B outputs take type-safe defaults, and `CrossBlocked` reports an enabled
but unready request. Ordering matters, so A-to-B and B-to-A are different tasks.

Every task is fixed before model screening and contains a natural-language
requirement, exact interface, reference implementation, formal properties,
independent OpenPLC test vectors, and an authored negative program. The OpenPLC
answers are composed from the original manually authored base-task oracles and the
explicit supervisory rules. The composite reference program is not executed to
produce these expected outputs. No easy/medium/hard label is used; the documented
complexity fields are descriptive attributes, not selection strata.

## Frozen verifier qualification

No Kimi call is permitted until all of the following hold for all 200 tasks:

1. Schema, interface, category balance, ordered-pair uniqueness, base-role balance, and file
   hashes pass deterministic validation.
2. The reference passes the frozen three-stage chain: MatIEC, then every supported
   mandatory PLCverif invariant, then OpenPLC compilation and functional execution.
3. The authored negative remains MatIEC-compilable and is rejected by PLCverif or
   OpenPLC. This calibration does not turn one negative into an additional task.

The qualification negative is a common supervisory sentinel, not a mutation-study
sample: it forces `CrossBlocked` to remain FALSE in the explicitly tested state
where subsystem B is requested before readiness. Structural validation requires
both a native PLCverif invariant and an independent OpenPLC observation for this
defect. Its purpose is to detect an insensitive judge; it does not measure mutation
coverage for the heterogeneous subsystem-A and subsystem-B logic.

## Kimi screening and selection

Screening uses Direct@1: exactly one stateless Kimi-K3 request per task, no
candidate repair, no feedback, and no reference, OpenPLC tests, or formal
properties in the prompt. A task is selection-eligible only if a model
response was received and the candidate failed a semantic gate. API failures,
timeouts, missing tools, validator-inconclusive outcomes, and protocol violations
are excluded rather than counted as model failures.

The selection quota is five eligible failures per category. When a category has
more than five, the predeclared rule chooses the five-task subset that maximizes
coverage of the five base behaviors in both subsystem-A and subsystem-B roles,
then minimizes role concentration and uses a seeded task-ID hash as a tie-break.
The rule does not use a difficulty label or a later loop-method result. If a
category has fewer than five, the selector fails; another category cannot fill the
quota. The complete 200-task screening ledger is retained, including successful
tasks and excluded runs.

The screening calls are used only to construct the challenge set. Every reported
baseline and loop-method result on `IEC-ST-VerifyBench-K3-Fail-50` must use fresh independent
calls. Papers must report both the model-conditioned selection process and, when
making broader performance claims, results on a separately sampled unscreened
set.

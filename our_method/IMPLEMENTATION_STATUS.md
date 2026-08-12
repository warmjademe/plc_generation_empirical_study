# Implementation status

Status date: 2026-08-10.

## Implemented and tested

| Component | Status | Evidence |
|---|---|---|
| One complete ST candidate per model call | Implemented | tagged response parser and attempt artifacts |
| Maximum 1--10 candidate budget | Implemented | constructor rejects values outside the range |
| Invalid/empty output consumes a candidate | Implemented | unit test |
| Stop on first visible pass | Implemented | unit test stops on candidate 2 |
| Sealed judge runs once and is terminal | Implemented | sealed-failure unit test |
| Kimi OpenAI-compatible client | Implemented | strict resolved-model check; no silent fallback |
| K3 complete assistant history | Implemented | preserves `reasoning_content`; unit test |
| Public prompt isolation | Implemented | loader opens only task requirement, interface, and public metadata |
| Fixed-interface validator | Implemented | checked against a dataset reference program |
| Deterministic scan-test adapter | Implemented | checked against the local IEC subset engine |
| External command/JSON validator adapters | Implemented | preflight, timeout, raw logs, hashes, structured statuses |
| Hash-chained evidence ledger | Implemented | tampering test |
| Requirement-level failure certificate | Implemented | deterministic priority and character budget |
| Non-regression anchor | Implemented | safety/requirement/gate lexicographic scoring |
| PATCH/RESTRUCTURE/RESTART policy | Implemented | deterministic policy code |
| Direct/Independent/RawRepair/EGBS modes | Implemented | common orchestrator and equal candidate accounting |

Eight unit/integration tests currently pass.  All 50 reference programs also pass
both authored scan suites in the local deterministic subset engine (100 suites).

The Boolean pilot additionally has a qualified, pinned chain: MatIEC 0.1,
PLCverif CLI 1.0.0.202410210930 with nuXmv 2.0.0, and OpenPLC v3 commit
`b5d41356dab4aeadca0dd7ca64ba542f870b595d`.  Both the reference and an `AND`-to-`OR`
negative control were exercised: the reference passed, while the negative control
produced a formal counterexample and an OpenPLC output mismatch.  These adapters
currently cover five stateless Boolean tasks only.  Qualification uses references,
authored negatives, and separate OpenPLC output-inversion sentinels.

Three clean Kimi K3 runs completed after qualification:

| Task | Difficulty/category | Candidates | PLCverif | Sealed OpenPLC |
|---|---|---:|---|---|
| `C01_E01_two_input_permissive` | easy / Boolean | 1 | 1/1 properties | 2/2 observations |
| `C01_M01_two_out_of_three_vote` | medium / Boolean | 1 | 2/2 properties | 3/3 observations |
| `C03_E01_forward_reverse_interlock` | easy / interlock | 1 | 3/3 properties | 2/2 observations |

All three hash-chained ledgers verified and each sealed judge was invoked once.
Aggregate model usage was 1,794 prompt tokens and 877 completion tokens.

## Required before the main empirical experiment

| Missing qualification | Why it blocks a paper-scale claim |
|---|---|
| Pin and execute MatIEC and/or RuSTy for the remaining reference and candidate programs | MatIEC is qualified for the five-task Boolean pilot, not all 50 tasks |
| Define every remaining custom property macro and build a deterministic PLCverif/SMV/monitor translator | Only propositional end-of-scan Boolean invariants are qualified |
| Validate the translator using reference programs and negative controls | Otherwise formal passes/failures may measure translation errors |
| Extend the independent OpenPLC judge beyond Boolean interfaces and simple scan timing | The five-task Boolean pilot is qualified; stateful, numeric, and timed tasks are not |
| Implement formal-counterexample replay and oracle-disagreement handling | The data fields and policy exist, but no backend currently produces replay decisions |
| Add resumable 50-task batch scheduling and aggregate statistics | Current CLI runs one task at a time |
| Complete independent task review and freeze hashes | Required to avoid changing the benchmark after seeing model outputs |

Consequently, the harness core is implemented, but the complete paper-grade method
is not finished.  It is suitable for mock tests and small development pilots.  A
50-task paid K3 run should wait until the mandatory compiler, formal, and sealed
runtime gates pass preflight.

## K3 credential compatibility

The private global credential file now records the supplied key.  A read-only model
list probe authenticated successfully against `https://api.kimi.com/coding/v1` and
returned `k3` and `k3-256k`; the same key did not authenticate against the Moonshot
public endpoint.  The repository contains only the provider URL, model ID, and
environment-variable name.  It contains no credential.

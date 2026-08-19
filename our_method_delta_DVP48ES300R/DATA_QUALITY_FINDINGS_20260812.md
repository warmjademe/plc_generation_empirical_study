# Development-set data-quality findings (2026-08-12)

These findings were discovered after inspecting terminal failures from the
DeepSeek v4 development run.  They must be resolved before the 50-task set is
used for a publication-level comparison.  They are not harness success claims.

## Out-of-contract vectors in C06_M02

`C06_M02_bounded_up_down_counter` states that `Capacity` remains constant during
a test and is positive.  The deterministic assumption audit found 211 scan
vectors with `Capacity <= 0`, including `boundary_001` with `Capacity = -1` and
`boundary_002` with `Capacity = 0`.  The v4 candidate's sealed failure on
`boundary_001` therefore occurred outside the public input domain.

The generated audit is `runs/dataset_assumption_audit_20260812.json`; the checker
is `scripts/audit_test_assumptions.py`.  Until the task is replaced or its
contract and oracle are revised consistently, its score must be reported as an
invalid benchmark observation rather than a model semantic failure.

## Scan-order ambiguity in C02_B08 and C02_B12

Both tasks state that safety loss while running or while a selected start is
present latches `B_RestartRequired`, and that a start presented while
`B_RestartRequired` is TRUE pulses `B_RejectedStart`.  Their hidden traces expect
`B_RejectedStart = FALSE` on the scan that first latches restart-required and
TRUE only on a later scan.  DeepSeek candidates that derived the pulse from the
new post-scan latch value failed this oracle.

The intended reference program implements safety loss in a higher-priority
`ELSIF` branch and therefore does not execute the rejection branch in the same
scan.  The natural-language contract does not explicitly say whether “while
restart-required is TRUE” refers to its scan-start or newly updated value.  The
task should state that the pulse requires restart-required to have already been
latched at scan start, or the oracle/property should be changed to permit the
post-update interpretation.

## Missing output semantics in C06_W03

`C06_W03_lean_composite` says that a rising `B_Item` edge increments `B_Count`
and that reset clears `B_Accepted`, but it never states when `B_Accepted` becomes
TRUE or that it is a one-scan pulse.  The hidden oracle expects `B_Accepted` TRUE
on an accepted rising edge and FALSE on the following low scan.  This behavior
appears in the metadata property but not in the natural-language task given to
the model.  The v4 candidate consequently passed the visible gates and failed
when it retained `B_Accepted` on the low scan.  The requirement must explicitly
define the output before this observation is scored as a synthesis defect.

## Evaluation consequence

v4 and v5 runs on the current task files are development diagnostics.  A paired
method comparison requires a frozen corrected manifest, requalification of the
reference and negative control, and rerunning every compared method on the same
corrected tasks.  Results from the current files remain useful for designing and
ablating public contract-risk handling, but not for an unbiased generalization
claim.

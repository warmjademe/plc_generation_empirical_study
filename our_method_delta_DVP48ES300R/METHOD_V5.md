# Agentic Context v5: contract risks and blind restarts

`agentic-context-v5.1-contract-risk-blind-restart-resource-recovery` is a
development revision.
It keeps the fixed MatIEC, PLCverif, visible OpenPLC, and OpenPLC final-verifier
implementations used by v4.  It changes only which public context is supplied to
the model and how a bounded ten-candidate budget is allocated.

Each run records hashes for the prompts, pattern cards, orchestrator, context and
repair policy, and every executable validator adapter.  This prevents a result
from being attributed to v5 after an unrecorded harness or feedback change.

## Mechanism 1: public contract-risk obligations

The harness deterministically scans the public requirement text for clauses that
commonly require explicit scan semantics: contrastive exceptions (`without`,
`unless`), guarded transitions (`only when`), one-scan pulses, simultaneous
priority, retained-state lifecycles, equivalences, and pre/post-scan events.  It
adds requirement-ID-aligned review obligations to the state packet.  This stage
does not read `reference.st`, `openplc_tests.json`, or `properties.json`, and its
output is not an oracle verdict.

## Mechanism 2: sealed-blind restart epochs

In v4, the first candidate to pass all visible gates was sent to the sealed
OpenPLC judge and a failure terminated the task, even when candidate budget
remained.  v5 permits at most three sealed candidate evaluations within the same
ten-candidate budget.  After a failure, the next epoch starts from the public
contract with no anchor, no previous assistant history, and no sealed inputs,
expected outputs, trace, diagnostic, requirement IDs, or candidate text.  A
fixed public schedule asks for structurally different treatments of contrastive
guards, pre-state events, transition/output separation, and minimal priority
chains.  The loop stops immediately on the first verified candidate.

This protocol measures bounded verifier pass@k, not one-shot generalization.
Repeated sealed pass/fail decisions are never model feedback, but they are still
multiple holdout queries.  Therefore v5 results on the current 50 tasks are
development evidence.  A publication claim requires a new task-level holdout
whose final judge is invoked according to a separately frozen evaluation rule.

## Mechanism 3: public duplicate guard

Before spending compiler, model-checker, simulator, or sealed-query budget, v5
compares the candidate hash with hashes of programs already generated in the
same task.  A byte-identical repeat is rejected with a public-only diversity
diagnostic and forces a structural restart.  No verifier result is needed for
this check, and a duplicate is never sent to the sealed judge twice.

## Corrected IEC edge context

The v4 public pattern card described every edge as `current AND NOT previous`,
which is only a rising edge.  This defect repeatedly induced rising-edge code for
`C04_S08_lean_composite`, whose public contract requires a falling edge.  v5
states both formulas explicitly and still updates previous-input memory only
after the scan decision.  This is a context bug fix, not an additional judge or
an oracle-derived hint.

## Stateful visible counterexamples

The v4 OpenPLC feedback reported only the failing scan.  For timers, counters,
and retained-state machines, that scan omits the prefix that produced the state,
so the repair model could not replay the failure it was instructed to inspect.
v5 adds a bounded public prefix: full initial inputs followed by input deltas and
the executed repeat count through the failing observation.  This prefix is
available only from authored visible cases; sealed evidence remains absent from
every model request.

## Verification-resource recovery

An IEC program can compile while creating a needlessly large formal state space,
for example by incrementing a retained `INT` forever after a timeout threshold.
The retrieved timer and counter cards therefore require threshold saturation.
If a mandatory verifier remains inconclusive after its infrastructure retry, v5
may spend at most one remaining candidate slot on a blind public-contract
resynthesis.  The timed-out candidate and tool diagnostic are not included in
the next model request, and an inconclusive result is never counted as a pass.

## Prespecified ablations

- `contract_risk_analysis=false` removes the requirement-risk packet.
- `sealed_rejection_policy=terminal` and `max_sealed_attempts=1` restore the v4
  per-task stopping rule.
- Replacing the profile list by one fixed profile tests whether diversity rather
  than additional verifier queries explains any gain.
- `duplicate_candidate_guard=false` permits repeated programs as in v4.
- Removing `--include-failure-prefix` from the visible OpenPLC validator restores
  single-scan v4 feedback without changing any test outcome.
- `inconclusive_recovery_policy=terminal` restores the v4 policy of ending a task
  after a mandatory verifier remains inconclusive.

Use `configs/deepseek_v4_flash_agentic_context_v5.json`.  The configuration is
marked `development_only`; no Kimi provider or fallback is permitted.

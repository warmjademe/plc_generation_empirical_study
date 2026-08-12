# Experimental design and contribution boundary

## Research object

The study does not ask whether an LLM can emit syntactically plausible ST.  It asks
whether organizing deterministic verification evidence improves the probability and
cost of finding a fully verified program under a fixed budget of ten complete
candidates.  A candidate is the unit of generation cost; an empty, truncated,
unparseable, or interface-changing answer consumes one candidate.

The full method is provisionally called Evidence-Guided Bounded Synthesis (EGBS).
The name is descriptive.  Novelty must be established against the closest 2025--2026
PLC-generation and verifier-guided repair work before submission.

## Fixed loop

```text
public task contract
    ↓
one model call: hypothesis + target requirement IDs + complete ST candidate
    ↓
interface / IEC profile gate
    ↓
compiler gate (MatIEC and/or RuSTy)
    ↓
visible deterministic scan tests
    ↓
mandatory formal properties through a deterministic ST translation
    ↓
counterexample replay and oracle-disagreement classification
    ↓
append-only evidence ledger and bounded failure certificate
    ↓
anchor selection + PATCH / RESTRUCTURE / RESTART
    ↺, at most 10 candidates
```

The first candidate passing every visible gate is frozen immediately.  A sealed
runtime judge is invoked once.  Its result is terminal and never enters a later
model prompt.  Ten candidates are a maximum, not a target.

## Mechanisms under test

### Requirement-aligned evidence ledger

Every observation links a candidate hash, validator/version, failure kind, relevant
requirement IDs, minimized trace, raw-log hash, and oracle status.  The ledger is
hash chained.  It records repeated errors and regressions instead of replacing the
history with the latest log.

### Failure certificate

The feedback packet is selected deterministically under a fixed character budget:
safety-related evidence, blocking compilation/interface failures, new signatures,
then shorter traces.  This prevents methods from gaining an uncontrolled context or
token advantage and makes feedback selection reproducible.

### Non-regression anchor

The next repair is not necessarily based on the newest candidate.  Candidates are
ranked lexicographically by supported safety requirements, all supported
requirements, passed gates, and distinct failures.  A later candidate that breaks a
previously supported safety requirement cannot displace a stronger anchor merely
because it is newer.

### Repair mode

- `PATCH`: one localized, confirmed defect;
- `RESTRUCTURE`: failures span multiple interacting requirements;
- `RESTART`: the same evidence signature repeats or requirement coverage does not
  improve across successive attempts;
- `SYNTHESIZE`: first attempt and independent-generation baselines.

The decision policy is fixed code; it is not an extra LLM call.  Every opportunity
therefore uses exactly one model response that contains a complete ST program.

### Cross-oracle evidence status

A formal counterexample should be replayed in an independent scan executor when its
state is observable.  Reproduced traces are `confirmed_candidate_defect`.  A trace
that cannot be replayed because the translation and runtime disagree is
`oracle_disagreement`, not a candidate failure.  An internal-state property that has
no runtime observation is `not_replayable`.  This classification is necessary
because generated or unqualified ST-to-SMV translations can otherwise create a
false stopping or repair signal.

## Baselines under identical budgets

| Method | Candidate budget | Uses feedback | Uses anchor/history |
|---|---:|---|---|
| Direct | 1 | No | No |
| Independent | 10 | No | No; every call is fresh |
| RawRepair | 10 | Latest bounded raw diagnostics | Latest candidate |
| EGBS | 10 | Requirement-level certificate | Best non-regressing anchor |

Each method must use the same Kimi snapshot, public task text, maximum output tokens,
and visible/sealed judges.  Wall-clock concurrency may be equalized separately from
candidate and token budgets.  Results from another paper's dataset cannot be used as
a direct performance comparison; all baselines must be rerun on these 50 paired
tasks.

## Research questions

- RQ1: Does evidence-guided bounded synthesis improve sealed verification success
  relative to raw-log repair under equal candidate and token budgets?
- RQ2: How does the method affect candidate, token, monetary, and wall-clock cost to
  reach a sealed pass?
- RQ3: What are the individual contributions of failure certificates,
  non-regression anchors, adaptive repair modes, and counterexample replay?
- RQ4: For which task and error categories does the loop fail within ten candidates?

## Ablations

- full EGBS minus requirement alignment (raw logs with the same character limit);
- minus non-regression anchor (always repair the latest candidate);
- minus adaptive mode (always `PATCH`);
- minus cross-oracle replay (all formal counterexamples treated as candidate defects);
- minus ledger history (only the newest signature is visible).

Only the strongest baseline and prespecified ablations should be primary
comparisons.  Additional variants are exploratory and require multiple-comparison
control.

## Outcomes and analysis

The primary outcome is paired task-level `VerifiedSuccess@10`.  Secondary outcomes
include cumulative success by candidate number, area under that curve, restricted
mean attempts with failures truncated at 11, visible-pass/sealed-fail rate, tokens
and cost per solved task, repeated-error rate, supported-requirement regression rate,
and oracle disagreements.

Use a paired exact test for the primary binary comparison, report the paired risk
difference with a confidence interval, and report odds ratios only with an exact or
small-sample interval.  Candidate-level records are dependent and must not be
treated as 500 independent observations.  Apply BH--FDR to secondary families and
report effect sizes and intervals even when p-values exceed a threshold.

## Failure conditions for the contribution claim

The evidence mechanism is not supported if the sealed success difference is
compatible with no practically relevant improvement, if benefits disappear under
equal token cost, if visible improvements increase the sealed generalization gap,
or if removing the proposed mechanisms does not reduce performance.  These are
valid empirical findings and should be reported rather than reframed as success.


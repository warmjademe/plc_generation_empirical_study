# PLC Generation Balanced-100

This dataset contains 100 IEC Structured Text generation tasks, with exactly ten
tasks in each of the ten control-behavior categories. It is rebuilt only from
previously generated task banks; dataset construction makes no LLM API calls.

## Selection rule

A task is eligible only when its historical qualification record shows that the
reference program passed MatIEC, PLCverif, and OpenPLC, and that the predeclared
negative control was rejected. Historical total reference-validation time must be
at most 600 seconds. The known problematic tasks listed in `selection_audit.json` are excluded
because a post-hoc audit found an input-assumption violation or an underspecified
contract/Oracle relationship.

Difficulty is operationalized without using the Kimi screening verdict. Within
each category, the builder computes percentile ranks for requirements,
interactions, transitions, retained state, stateful blocks, fault modes, scan
horizon, inputs, and outputs. Their equal-weight mean is the structural-complexity
score. Selection then maximizes, in order: distinct unordered composition pairs,
distinct base behaviors, summed structural complexity, and shorter historical
qualification time. This balances semantic coverage and structural challenge
without selecting tasks merely because one target model failed them.

Kimi screening outcomes are retained only as descriptive provenance. Both prior
successes and failures may be included, and tasks without a Kimi run remain
eligible.

## Verification status

`selection_audit.json` records the immutable source qualification evidence and
selection calculation. `structural_audit.json` checks balance, hashes,
interface/Oracle consistency, feedback/sealed split presence, and known
exclusions. A separate exact calibration must run all 100 reference programs
through the current MatIEC -> PLCverif -> OpenPLC configuration before the
dataset is used for a scored experiment. The resulting report belongs under
`evidence/revalidation/`.

Automatic checks do not replace independent human review of natural-language
contracts and scan-order semantics. The dataset remains a development artifact
until that review is complete and the manifest is frozen for all compared
methods.

## Rebuild

From this directory, supply the compact qualification catalog exported from the
NAS qualification runs:

```bash
python3 build_dataset.py --qualification-catalog /path/to/catalog.json
python3 audit_dataset.py
```

The builder refuses to overwrite an existing `tasks/` tree or manifest.

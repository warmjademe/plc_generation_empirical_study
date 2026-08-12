# Task schema

## metadata.json

Required fields include task identity, category, difficulty, IEC features, complexity
vector, interface, scan semantics, assumptions, and requirement records.  Difficulty
is assigned before running any evaluated model.

The complexity vector records:

- number of inputs and outputs;
- number of requirements;
- number of retained state variables;
- number of state transitions;
- number of stateful standard blocks;
- number of interacting requirement pairs;
- number of fault/recovery modes;
- maximum relevant scan horizon.

Raw values are retained even when the categorical difficulty label is used.

## properties.json

Properties use a small, tool-neutral temporal notation:

- `G(expr)`: `expr` must hold at every observed end-of-scan state;
- `X(expr)`: `expr` must hold at the next end-of-scan state;
- `rose(x)` and `fell(x)`: edge predicates between adjacent scans;
- `a U b`: `a` holds until `b` holds;
- `within(n, trigger, response)`: after `trigger`, `response` occurs within `n`
  scans, subject to the stated environment assumptions.

These expressions are requirements interchange, not direct nuXmv input.  A pinned,
deterministic translator must produce backend syntax.  The evaluated LLM must not
write or alter the translation.

Every property contains one or more `requirement_ids` and is marked `mandatory` or
`diagnostic`.

## tests_feedback.json and tests_hidden.json

Each test starts from a fresh instance and contains ordered steps.  A step defines
input values, expected output values, and the number of scans for which the step is
repeated.  The expected values are checked at the end of each repeated scan unless
`check` is `last_only`.

Feedback tests may return a minimized trace to the generation loop.  Hidden tests are
executed after candidate selection and are never returned to the method under test.
Hidden tests do not introduce new requirements; they use new traces, boundaries, and
conflicting inputs for the same published contract.

## negative_control

Each task contains one optional seeded-fault specification and one generated faulty
program.  The index records the operator, target requirement, expected detection
mechanism, and validation status.  A negative control is a local quality check for
the oracles: it is not sent to an LLM, does not count as an additional generation
task, and may be omitted from the cost-constrained model experiment.

## validation_report.json

The report separates structural validation from external tools.  Allowed status
values are `pass`, `fail`, `inconclusive`, and `not_run`.  A field may not be set to
`pass` without captured tool output and a pinned tool version.

# C08_M01_branching_sorter: Branching item sorter sequence

## Objective

Implement `C08_M01_branching_sorter` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: ItemPresent in wait state shall enter inspection.
- **R2**: Inspection shall branch to reject when RejectClass is TRUE and to accept otherwise.
- **R3**: TransferDone in either transfer state shall return to wait.
- **R4** **[safety-critical]**: Inspect, AcceptGate, and RejectGate shall be mutually exclusive and match State.
- **R5** **[safety-critical]**: Reset shall return to wait and close both gates.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

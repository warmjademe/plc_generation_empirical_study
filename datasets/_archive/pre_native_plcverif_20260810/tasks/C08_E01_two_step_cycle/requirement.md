# C08_E01_two_step_cycle: Two-step process cycle

## Objective

Implement `C08_E01_two_step_cycle` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start in idle shall enter Step 1.
- **R2**: Step1Done in Step 1 shall enter Step 2.
- **R3**: Step2Done in Step 2 shall enter complete state.
- **R4** **[safety-critical]**: Only the output corresponding to the current active step shall be TRUE; Complete is TRUE only in state 3.
- **R5**: Reset shall return to idle from any state.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C10_H02_fair_resource_arbiter: Fair two-client resource arbiter with emergency lockout

## Objective

Implement `C10_H02_fair_resource_arbiter` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: GrantA and GrantB shall never be TRUE simultaneously.
- **R2**: When idle, a single request shall receive the resource; simultaneous requests shall follow Turn.
- **R3**: Done shall release the resource before a new owner is selected on a later scan.
- **R4**: After A completes Turn shall prefer B, and after B completes Turn shall prefer A.
- **R5** **[safety-critical]**: Emergency shall immediately revoke all grants and latch LockedOut.
- **R6**: Reset shall clear LockedOut only while Emergency and both requests are FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C06_X01_batch_quality_lockout: Edge-counted batch with consecutive-reject lockout

## Objective

Implement `C06_X01_batch_quality_lockout` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Only a rising ItemPulse while not stopped, complete, or locked shall count one item.
- **R2**: An accepted item increments AcceptedCount and clears ConsecutiveRejects; a rejected item increments both reject counters.
- **R3**: Complete shall latch when AcceptedCount reaches positive Target and no later item may change counts.
- **R4** **[safety-critical]**: Except for a qualified reset scan, RejectLimit less than or equal to zero, or reaching RejectLimit consecutive rejects, shall latch LockedOut.
- **R5** **[safety-critical]**: Stop has priority over ItemPulse and prevents every count change.
- **R6**: Reset clears all state only while Stop is TRUE and ItemPulse is FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Target and RejectLimit remain constant during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

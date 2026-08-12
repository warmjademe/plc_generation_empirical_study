# C06_W15_lean_composite: Composed supervisory control: Two-out-of-three sensor voter -> Edge-counted batch with consecutive-reject lockout

## Objective

Implement `C06_W15_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Vote shall be TRUE when at least two of A_S1, A_S2, and A_S3 are TRUE.
- **R2**: Subsystem A shall satisfy: A_Unanimous shall be TRUE only when all three channels have the same value.
- **R3**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_ItemPulse while not stopped, B_Complete, or locked shall count one item.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An accepted item increments B_AcceptedCount and clears B_ConsecutiveRejects; a B_Rejected item increments both reject counters.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Complete shall latch when B_AcceptedCount reaches positive B_Target and no later item may change counts.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Except for a qualified B_Reset scan, B_RejectLimit less than or equal to zero, or reaching B_RejectLimit consecutive rejects, shall latch B_LockedOut.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop has priority over B_ItemPulse and prevents every count change.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears all state only while B_Stop is TRUE and B_ItemPulse is FALSE.
- **R9** **[safety-critical]**: A TRUE A_Vote shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem B: B_Target and B_RejectLimit remain constant during a test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_Target remains within the closed interval [-4, 4] during a test.
- B_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

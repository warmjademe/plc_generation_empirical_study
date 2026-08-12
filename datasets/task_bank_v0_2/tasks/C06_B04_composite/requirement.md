# C06_B04_composite: Composed supervisory control: Good/reject batch statistics with reject lockout -> Edge-counted batch with consecutive-reject lockout

## Objective

Implement `C06_B04_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A good-part rising edge increments only A_GoodCount; a reject-part rising edge increments only A_RejectCount.
- **R2**: Subsystem A shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_GoodCount plus A_RejectCount reaches A_BatchTarget.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_QualityFault shall latch when A_RejectCount reaches A_RejectLimit and remain set until A_Reset.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear both counts, A_BatchDone, and A_QualityFault.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_ItemPulse while not stopped, B_Complete, or locked shall count one item.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An accepted item increments B_AcceptedCount and clears B_ConsecutiveRejects; a B_Rejected item increments both reject counters.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Complete shall latch when B_AcceptedCount reaches positive B_Target and no later item may change counts.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_RejectLimit less than or equal to zero, or reaching B_RejectLimit consecutive rejects, shall latch B_LockedOut.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop has priority over B_ItemPulse and prevents every count change.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears all state only while B_Stop is TRUE and B_ItemPulse is FALSE.
- **R12** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- BatchTarget and RejectLimit remain positive and constant during a test.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

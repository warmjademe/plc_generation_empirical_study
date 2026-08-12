# C06_B17_composite: Composed supervisory control: Edge-counted batch with consecutive-reject lockout -> Good/reject batch statistics with reject lockout

## Objective

Implement `C06_B17_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Only a rising A_ItemPulse while not stopped, A_Complete, or locked shall count one item.
- **R2**: Subsystem A shall satisfy: An accepted item increments A_AcceptedCount and clears A_ConsecutiveRejects; a A_Rejected item increments both reject counters.
- **R3**: Subsystem A shall satisfy: A_Complete shall latch when A_AcceptedCount reaches positive A_Target and no later item may change counts.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_RejectLimit less than or equal to zero, or reaching A_RejectLimit consecutive rejects, shall latch A_LockedOut.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Stop has priority over A_ItemPulse and prevents every count change.
- **R6**: Subsystem A shall satisfy: A_Reset clears all state only while A_Stop is TRUE and A_ItemPulse is FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A good-part rising edge increments only B_GoodCount; a reject-part rising edge increments only B_RejectCount.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_GoodCount plus B_RejectCount reaches B_BatchTarget.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_QualityFault shall latch when B_RejectCount reaches B_RejectLimit and remain set until B_Reset.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear both counts, B_BatchDone, and B_QualityFault.
- **R12** **[safety-critical]**: A TRUE A_Complete shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- BatchTarget and RejectLimit remain positive and constant during a test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

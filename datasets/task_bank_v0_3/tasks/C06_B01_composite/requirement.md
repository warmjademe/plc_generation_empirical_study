# C06_B01_composite: Composed supervisory control: Good/reject batch statistics with reject lockout -> Inspection-window reject lockout

## Objective

Implement `C06_B01_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A good-part rising edge increments only A_GoodCount; a reject-part rising edge increments only A_RejectCount.
- **R2**: Subsystem A shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_GoodCount plus A_RejectCount reaches A_BatchTarget.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_QualityFault shall latch when A_RejectCount reaches A_RejectLimit and remain set until A_Reset.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear both counts, A_BatchDone, and A_QualityFault.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Inspected edge shall add one to B_WindowCount and, when B_Rejected is TRUE, one to B_RejectCount.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Completing B_WindowSize items shall pulse B_WindowComplete for one scan and then start a new zeroed window.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If rejects in the completed window exceed B_RejectLimit, B_LockedOut shall latch TRUE.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: No new items shall be counted while B_LockedOut.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear counts, B_WindowComplete, and B_LockedOut.
- **R11** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_BatchTarget and A_RejectLimit remain positive and constant during a test.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_WindowSize is at least 1 and B_RejectLimit is non-negative.
- Subsystem B: B_Rejected is sampled only on a rising B_Inspected edge.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

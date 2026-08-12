# C06_R04_lean_composite: Composed supervisory control: Good/reject batch statistics with reject lockout -> Mode-dependent command selection

## Objective

Implement `C06_R04_lean_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A good-part rising edge increments only A_GoodCount; a reject-part rising edge increments only A_RejectCount.
- **R2**: Subsystem A shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_GoodCount plus A_RejectCount reaches A_BatchTarget.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_QualityFault shall latch when A_RejectCount reaches A_RejectLimit and remain set until A_Reset.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear both counts, A_BatchDone, and A_QualityFault.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Command shall follow B_AutoDemand in automatic mode and B_ManualDemand in manual mode, but only when B_SafetyOK is TRUE and B_Inhibit is FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or B_Inhibit is TRUE.
- **R8** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_BatchTarget and A_RejectLimit remain positive and constant during a test.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- A_BatchTarget remains within the closed interval [-4, 4] during a test.
- A_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

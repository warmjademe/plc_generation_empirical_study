# C06_W21_lean_composite: Composed supervisory control: Voted permissive with qualified bypass and diagnostics -> Good/reject batch statistics with reject lockout

## Objective

Implement `C06_W21_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: The selected request shall be A_AutoRequest in automatic mode and A_ManualRequest otherwise.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Without bypass, A_RunPermit requires A_SafetyOK and at least two TRUE channels.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Bypass may latch only in manual mode when A_BypassRequest, A_BypassPermit, A_SafetyOK, and at least one channel are TRUE.
- **R4**: Subsystem A shall satisfy: A_Reset may clear A_BypassActive only when neither automatic nor manual request is active.
- **R5**: Subsystem A shall satisfy: A_Degraded shall identify a permitted run with channel disagreement or active bypass; A_Blocked shall identify a selected request without A_RunPermit.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A good-part rising edge increments only B_GoodCount; a reject-part rising edge increments only B_RejectCount.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_GoodCount plus B_RejectCount reaches B_BatchTarget.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_QualityFault shall latch when B_RejectCount reaches B_RejectLimit and remain set until B_Reset.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear both counts, B_BatchDone, and B_QualityFault.
- **R11** **[safety-critical]**: A TRUE A_RunPermit shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_BatchTarget and B_RejectLimit remain positive and constant during a test.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_BatchTarget remains within the closed interval [-4, 4] during a test.
- B_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C06_V24_lean_composite: Composed supervisory control: Voted permissive with qualified bypass and diagnostics -> Bounded up/down inventory counter

## Objective

Implement `C06_V24_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: The selected request shall be A_AutoRequest in automatic mode and A_ManualRequest otherwise.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Without bypass, A_RunPermit requires A_SafetyOK and at least two TRUE channels.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Bypass may latch only in manual mode when A_BypassRequest, A_BypassPermit, A_SafetyOK, and at least one channel are TRUE.
- **R4**: Subsystem A shall satisfy: A_Reset may clear A_BypassActive only when neither automatic nor manual request is active.
- **R5**: Subsystem A shall satisfy: A_Degraded shall identify a permitted run with channel disagreement or active bypass; A_Blocked shall identify a selected request without A_RunPermit.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A lone rising B_AddItem edge increments B_Count when below B_Capacity.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A lone rising B_RemoveItem edge decrements B_Count when above zero.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous rising edges shall leave B_Count unchanged and set B_Conflict for one scan.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain within zero and B_Capacity; B_Empty and B_Full reflect the boundaries.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count and B_Conflict.
- **R11** **[safety-critical]**: A TRUE A_RunPermit shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_Capacity remains constant during a test and is positive.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_Capacity remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

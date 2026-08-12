# C06_U20_lean_composite: Composed supervisory control: Bounded up/down inventory counter -> Voted permissive with qualified bypass and diagnostics

## Objective

Implement `C06_U20_lean_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A lone rising A_AddItem edge increments A_Count when below A_Capacity.
- **R2**: Subsystem A shall satisfy: A lone rising A_RemoveItem edge decrements A_Count when above zero.
- **R3**: Subsystem A shall satisfy: Simultaneous rising edges shall leave A_Count unchanged and set A_Conflict for one scan.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall remain within zero and A_Capacity; A_Empty and A_Full reflect the boundaries.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Count and A_Conflict.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The selected request shall be B_AutoRequest in automatic mode and B_ManualRequest otherwise.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Without bypass, B_RunPermit requires B_SafetyOK and at least two TRUE channels.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Bypass may latch only in manual mode when B_BypassRequest, B_BypassPermit, B_SafetyOK, and at least one channel are TRUE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset may clear B_BypassActive only when neither automatic nor manual request is active.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Degraded shall identify a permitted run with channel disagreement or active bypass; B_Blocked shall identify a selected request without B_RunPermit.
- **R11** **[safety-critical]**: A TRUE A_Empty shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_Capacity remains constant during a test and is positive.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- A_Capacity remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

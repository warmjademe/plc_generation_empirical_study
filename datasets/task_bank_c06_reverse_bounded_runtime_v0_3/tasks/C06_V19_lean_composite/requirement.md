# C06_V19_lean_composite: Composed supervisory control: Mode-dependent command selection -> Bounded up/down inventory counter

## Objective

Implement `C06_V19_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Command shall follow A_AutoDemand in automatic mode and A_ManualDemand in manual mode, but only when A_SafetyOK is TRUE and A_Inhibit is FALSE.
- **R2**: Subsystem A shall satisfy: A_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or A_Inhibit is TRUE.
- **R3**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A lone rising B_AddItem edge increments B_Count when below B_Capacity.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A lone rising B_RemoveItem edge decrements B_Count when above zero.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous rising edges shall leave B_Count unchanged and set B_Conflict for one scan.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain within zero and B_Capacity; B_Empty and B_Full reflect the boundaries.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count and B_Conflict.
- **R8** **[safety-critical]**: A TRUE A_Command shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

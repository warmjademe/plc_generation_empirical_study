# C04_R24_lean_composite: Composed supervisory control: Qualified dual-edge recorder with saturation and re-arm -> Mode-dependent command selection

## Objective

Implement `C04_R24_lean_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Only a qualified, non-inhibited rising edge observed while not previously A_Locked may be accepted.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Simultaneous eligible edges shall accept A only.
- **R3**: Subsystem A shall satisfy: Each accepted event increments A_Count once and records A_LastSource.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Except for a qualified A_Reset scan, A_Count shall saturate at A_MaxCount and latch A_Locked; A_MaxCount less than or equal to zero locks without counting.
- **R5**: Subsystem A shall satisfy: A held-high event shall not retrigger until observed low and then rising again.
- **R6**: Subsystem A shall satisfy: A_Reset clears A_Count, A_Locked, and A_LastSource only while both events are low.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Command shall follow B_AutoDemand in automatic mode and B_ManualDemand in manual mode, but only when B_SafetyOK is TRUE and B_Inhibit is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or B_Inhibit is TRUE.
- **R9** **[safety-critical]**: A TRUE A_PulseA shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem A: A_MaxCount remains constant during a test.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

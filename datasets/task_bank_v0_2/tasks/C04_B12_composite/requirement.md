# C04_B12_composite: Composed supervisory control: Armed falling-edge pulse -> Qualified dual-edge recorder with saturation and re-arm

## Objective

Implement `C04_B12_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Armed shall equal A_Arm at the end of each scan.
- **R2**: Subsystem A shall satisfy: A_Pulse shall occur on a TRUE-to-FALSE A_Signal transition only when A_Arm is TRUE.
- **R3**: Subsystem A shall satisfy: Disarming shall suppress A_Pulse without corrupting future edge detection.
- **R4** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a qualified, non-inhibited rising edge may be accepted.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous eligible edges shall accept A only.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each accepted event increments B_Count once and records B_LastSource.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall saturate at B_MaxCount and latch B_Locked; B_MaxCount less than or equal to zero locks without counting.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A held-high event shall not retrigger until observed low and then rising again.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Count, B_Locked, and B_LastSource only while both events are low.
- **R10** **[safety-critical]**: A TRUE A_Pulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

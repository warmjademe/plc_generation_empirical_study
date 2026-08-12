# C04_B08_composite: Composed supervisory control: Dual-event priority capture with lockout -> Qualified dual-edge recorder with saturation and re-arm

## Objective

Implement `C04_B08_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Reset shall clear A_Captured, A_Code, and A_Pulse.
- **R2**: Subsystem A shall satisfy: While armed and not A_Captured, a rising A_EventA shall capture A_Code 1.
- **R3**: Subsystem A shall satisfy: A simultaneous rising edge shall select A_EventA over A_EventB.
- **R4**: Subsystem A shall satisfy: A rising A_EventB without A_EventA shall capture A_Code 2.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: After capture, later events shall not change A_Code until A_Reset.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a qualified, non-inhibited rising edge may be accepted.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous eligible edges shall accept A only.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each accepted event increments B_Count once and records B_LastSource.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall saturate at B_MaxCount and latch B_Locked; B_MaxCount less than or equal to zero locks without counting.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A held-high event shall not retrigger until observed low and then rising again.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Count, B_Locked, and B_LastSource only while both events are low.
- **R12** **[safety-critical]**: A TRUE A_Captured shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

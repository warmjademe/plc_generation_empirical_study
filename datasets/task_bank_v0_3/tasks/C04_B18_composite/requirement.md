# C04_B18_composite: Composed supervisory control: Qualified dual-edge recorder with saturation and re-arm -> Dual-event priority capture with lockout

## Objective

Implement `C04_B18_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Only a qualified, non-inhibited rising edge observed while not previously A_Locked may be accepted.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Simultaneous eligible edges shall accept A only.
- **R3**: Subsystem A shall satisfy: Each accepted event increments A_Count once and records A_LastSource.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Except for a qualified A_Reset scan, A_Count shall saturate at A_MaxCount and latch A_Locked; A_MaxCount less than or equal to zero locks without counting.
- **R5**: Subsystem A shall satisfy: A held-high event shall not retrigger until observed low and then rising again.
- **R6**: Subsystem A shall satisfy: A_Reset clears A_Count, A_Locked, and A_LastSource only while both events are low.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Captured, B_Code, and B_Pulse.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While armed and not B_Captured, a rising B_EventA shall capture B_Code 1.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A simultaneous rising edge shall select B_EventA over B_EventB.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A rising B_EventB without B_EventA shall capture B_Code 2.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After capture, later events shall not change B_Code until B_Reset.
- **R12** **[safety-critical]**: A TRUE A_PulseA shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

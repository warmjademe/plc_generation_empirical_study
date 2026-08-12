# C04_B07_composite: Composed supervisory control: Dual-event priority capture with lockout -> Toggle output on qualified rising edge

## Objective

Implement `C04_B07_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Reset shall clear A_Captured, A_Code, and A_Pulse.
- **R2**: Subsystem A shall satisfy: While armed and not A_Captured, a rising A_EventA shall capture A_Code 1.
- **R3**: Subsystem A shall satisfy: A simultaneous rising edge shall select A_EventA over A_EventB.
- **R4**: Subsystem A shall satisfy: A rising A_EventB without A_EventA shall capture A_Code 2.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: After capture, later events shall not change A_Code until A_Reset.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_State and suppress B_AcceptedPulse with highest priority.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A rising B_Button edge while B_Enable is TRUE shall invert B_State exactly once.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Holding B_Button TRUE shall not repeatedly toggle B_State.
- **R9** **[safety-critical]**: A TRUE A_Captured shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C04_B15_composite: Composed supervisory control: Toggle output on qualified rising edge -> Armed falling-edge pulse

## Objective

Implement `C04_B15_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Reset shall clear A_State and suppress A_AcceptedPulse with highest priority.
- **R2**: Subsystem A shall satisfy: A rising A_Button edge while A_Enable is TRUE shall invert A_State exactly once.
- **R3**: Subsystem A shall satisfy: Holding A_Button TRUE shall not repeatedly toggle A_State.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Armed shall equal B_Arm at the end of each scan.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pulse shall occur on a TRUE-to-FALSE B_Signal transition only when B_Arm is TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disarming shall suppress B_Pulse without corrupting future edge detection.
- **R7** **[safety-critical]**: A TRUE A_State shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R8** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R9**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R10** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

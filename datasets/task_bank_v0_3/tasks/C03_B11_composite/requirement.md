# C03_B11_composite: Composed supervisory control: Pump and discharge-valve interlock -> Mutually exclusive heating and cooling with deadband

## Objective

Implement `C03_B11_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_ValveCommand shall follow a valid A_RunRequest while A_TankLevelOK and not A_Stop hold.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand requires A_ValveFeedbackOpen in addition to the valve-command permissives.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand shall be FALSE when A_Stop or loss of A_TankLevelOK is active.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_InterlockAlarm shall be TRUE when A_PumpFeedback is TRUE while valve feedback is closed.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Heat shall turn on below B_Setpoint minus 1.0 while enabled and safe.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Cool shall turn on above B_Setpoint plus 1.0 while enabled and safe.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Neither output shall be active inside the inclusive deadband.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Heat and B_Cool shall never be active together, and B_SafetyTrip shall turn both off.
- **R9** **[safety-critical]**: A TRUE A_ValveCommand shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

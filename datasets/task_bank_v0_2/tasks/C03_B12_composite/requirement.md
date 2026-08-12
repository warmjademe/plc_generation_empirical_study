# C03_B12_composite: Composed supervisory control: Pump and discharge-valve interlock -> Ventilated heater startup with proof timeout

## Objective

Implement `C03_B12_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_ValveCommand shall follow a valid A_RunRequest while A_TankLevelOK and not A_Stop hold.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand requires A_ValveFeedbackOpen in addition to the valve-command permissives.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_PumpCommand shall be FALSE when A_Stop or loss of A_TankLevelOK is active.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_InterlockAlarm shall be TRUE when A_PumpFeedback is TRUE while valve feedback is closed.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A healthy B_HeatRequest shall enter ventilation proving and command the damper and fan before the heater.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_HeaterCommand may energize only after B_DamperOpen and B_AirflowOK remain TRUE for 300 ms.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Failure to establish both proofs within 600 ms shall latch B_Fault and force all commands FALSE.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_GuardClosed, B_DamperOpen, or B_AirflowOK while heating shall immediately trip and latch B_Fault.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall return to idle without clearing B_Fault; B_Reset clears B_Fault only while idle with B_HeatRequest FALSE.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_HeaterCommand shall never be TRUE unless B_DamperCommand and B_FanCommand are both TRUE.
- **R11** **[safety-critical]**: A TRUE A_ValveCommand shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- The runtime scan period is 100 ms.
- Proof inputs are sampled at scan start.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

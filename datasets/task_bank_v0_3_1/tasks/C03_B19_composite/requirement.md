# C03_B19_composite: Composed supervisory control: Ventilated heater startup with proof timeout -> Pump and discharge-valve interlock

## Objective

Implement `C03_B19_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A healthy A_HeatRequest shall enter ventilation proving and command the damper and fan before the heater.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_HeaterCommand may energize only after A_DamperOpen and A_AirflowOK remain TRUE for 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Failure to establish both proofs within 600 ms shall latch A_Fault and force all commands FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_GuardClosed, A_DamperOpen, or A_AirflowOK while heating shall immediately trip and latch A_Fault.
- **R5**: Subsystem A shall satisfy: A_Stop shall return to idle without clearing A_Fault; A_Reset clears A_Fault only while idle with A_HeatRequest FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_HeaterCommand shall never be TRUE unless A_DamperCommand and A_FanCommand are both TRUE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ValveCommand shall follow a valid B_RunRequest while B_TankLevelOK and not B_Stop hold.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_PumpCommand requires B_ValveFeedbackOpen in addition to the valve-command permissives.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_PumpCommand shall be FALSE when B_Stop or loss of B_TankLevelOK is active.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_InterlockAlarm shall be TRUE when B_PumpFeedback is TRUE while valve feedback is closed.
- **R11** **[safety-critical]**: A TRUE A_DamperCommand shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: Proof inputs are sampled at scan start.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

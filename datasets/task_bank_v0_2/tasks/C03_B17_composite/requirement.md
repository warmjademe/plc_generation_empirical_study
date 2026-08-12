# C03_B17_composite: Composed supervisory control: Ventilated heater startup with proof timeout -> Three-conveyor downstream interlock

## Objective

Implement `C03_B17_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A healthy A_HeatRequest shall enter ventilation proving and command the damper and fan before the heater.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_HeaterCommand may energize only after A_DamperOpen and A_AirflowOK remain TRUE for 300 ms.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Failure to establish both proofs within 600 ms shall latch A_Fault and force all commands FALSE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Loss of A_GuardClosed, A_DamperOpen, or A_AirflowOK while heating shall immediately trip and latch A_Fault.
- **R5**: Subsystem A shall satisfy: A_Stop shall return to idle without clearing A_Fault; A_Reset clears A_Fault only while idle with A_HeatRequest FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_HeaterCommand shall never be TRUE unless A_DamperCommand and A_FanCommand are both TRUE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C3Run shall require B_RunRequest, B_C3Available, B_C3Clear, and not B_Stop.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C2Run shall require B_C3Run, B_C2Available, and B_C2Clear.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_C1Run shall require B_C2Run and B_C1Clear.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall turn all three commands off.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall indicate B_RunRequest with at least one unavailable or uncleared stage.
- **R12** **[safety-critical]**: A TRUE A_DamperCommand shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Proof inputs are sampled at scan start.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

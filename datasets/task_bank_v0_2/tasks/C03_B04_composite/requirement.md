# C03_B04_composite: Composed supervisory control: Three-conveyor downstream interlock -> Ventilated heater startup with proof timeout

## Objective

Implement `C03_B04_composite` as an IEC-ST Core v1 function block in the Interlocks and safe outputs category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_C3Run shall require A_RunRequest, A_C3Available, A_C3Clear, and not A_Stop.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_C2Run shall require A_C3Run, A_C2Available, and A_C2Clear.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_C1Run shall require A_C2Run and A_C1Clear.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall turn all three commands off.
- **R5**: Subsystem A shall satisfy: A_Blocked shall indicate A_RunRequest with at least one unavailable or uncleared stage.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A healthy B_HeatRequest shall enter ventilation proving and command the damper and fan before the heater.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_HeaterCommand may energize only after B_DamperOpen and B_AirflowOK remain TRUE for 300 ms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Failure to establish both proofs within 600 ms shall latch B_Fault and force all commands FALSE.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Loss of B_GuardClosed, B_DamperOpen, or B_AirflowOK while heating shall immediately trip and latch B_Fault.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall return to idle without clearing B_Fault; B_Reset clears B_Fault only while idle with B_HeatRequest FALSE.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_HeaterCommand shall never be TRUE unless B_DamperCommand and B_FanCommand are both TRUE.
- **R12** **[safety-critical]**: A TRUE A_C1Run shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

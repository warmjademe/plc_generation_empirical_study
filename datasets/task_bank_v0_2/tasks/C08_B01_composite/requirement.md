# C08_B01_composite: Composed supervisory control: Pause/resume sequence with abort recovery -> State sequence with per-stage timeout

## Objective

Implement `C08_B01_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start shall begin Step 1 only when idle and not A_Aborted.
- **R2**: Subsystem A shall satisfy: A_Advance shall move Step 1 to Step 2 and Step 2 to done only while not A_Paused.
- **R3**: Subsystem A shall satisfy: A_Pause shall suppress active step outputs without losing A_State; A_Resume clears A_Paused.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall return A_State to idle, suppress outputs, clear A_Paused, and latch A_Aborted.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Aborted only while A_Start, A_Advance, A_Pause, A_Resume, and A_Abort are all FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start in idle shall enter stage 1 and energize only B_Actuator1.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Sensor1 shall transition stage 1 to stage 2; B_Sensor2 shall B_Complete stage 2 and return idle.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Either stage remaining incomplete for 500 ms shall latch B_Fault and return idle with both actuators off.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall return idle and turn both actuators off without clearing B_Fault.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ResetFault clears B_Fault only while B_Stop is TRUE and B_Start is FALSE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Complete shall pulse only on the stage-2-to-idle completion transition.
- **R12** **[safety-critical]**: A TRUE A_Step1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- The runtime scan period is 100 ms.
- Sensor completion is expected within 500 ms of entering each stage.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

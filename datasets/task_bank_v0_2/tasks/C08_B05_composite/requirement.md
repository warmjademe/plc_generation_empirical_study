# C08_B05_composite: Composed supervisory control: State sequence with per-stage timeout -> Pause/resume sequence with abort recovery

## Objective

Implement `C08_B05_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1 and energize only A_Actuator1.
- **R2**: Subsystem A shall satisfy: A_Sensor1 shall transition stage 1 to stage 2; A_Sensor2 shall A_Complete stage 2 and return idle.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Either stage remaining incomplete for 500 ms shall latch A_Fault and return idle with both actuators off.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall return idle and turn both actuators off without clearing A_Fault.
- **R5**: Subsystem A shall satisfy: A_ResetFault clears A_Fault only while A_Stop is TRUE and A_Start is FALSE.
- **R6**: Subsystem A shall satisfy: A_Complete shall pulse only on the stage-2-to-idle completion transition.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start shall begin Step 1 only when idle and not B_Aborted.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Advance shall move Step 1 to Step 2 and Step 2 to done only while not B_Paused.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pause shall suppress active step outputs without losing B_State; B_Resume clears B_Paused.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall return B_State to idle, suppress outputs, clear B_Paused, and latch B_Aborted.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Aborted only while B_Start, B_Advance, B_Pause, B_Resume, and B_Abort are all FALSE.
- **R12** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Sensor completion is expected within 500 ms of entering each stage.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

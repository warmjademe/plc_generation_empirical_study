# C08_B08_composite: Composed supervisory control: State sequence with per-stage timeout -> Paused three-stage sequence with abort and per-stage timeout

## Objective

Implement `C08_B08_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start in idle shall enter stage 1 and energize only A_Actuator1.
- **R2**: Subsystem A shall satisfy: A_Sensor1 shall transition stage 1 to stage 2; A_Sensor2 shall A_Complete stage 2 and return idle.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Either stage remaining incomplete for 500 ms shall latch A_Fault and return idle with both actuators off.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall return idle and turn both actuators off without clearing A_Fault.
- **R5**: Subsystem A shall satisfy: A_ResetFault clears A_Fault only while A_Stop is TRUE and A_Start is FALSE.
- **R6**: Subsystem A shall satisfy: A_Complete shall pulse only on the stage-2-to-idle completion transition.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and B_Stage3Done returns idle with a one-scan B_Complete pulse.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pause shall retain B_State while forcing every actuator FALSE; Done inputs while B_Paused shall not advance.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The active stage shall time out after 500 ms of unpaused execution and latch B_Fault.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall immediately return idle, force safe outputs, and latch B_Fault.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only in idle while B_Start, B_Abort, and every Done input are FALSE.
- **R12** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At most one actuator may be TRUE, and B_Complete shall never coincide with an actuator.
- **R13** **[safety-critical]**: A TRUE A_Actuator1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Sensor completion is expected within 500 ms of entering each stage.
- Each test starts from a fresh function-block instance.
- Pausing resets rather than accumulates the stage timeout.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

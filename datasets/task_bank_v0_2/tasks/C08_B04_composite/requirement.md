# C08_B04_composite: Composed supervisory control: Pause/resume sequence with abort recovery -> Paused three-stage sequence with abort and per-stage timeout

## Objective

Implement `C08_B04_composite` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Start shall begin Step 1 only when idle and not A_Aborted.
- **R2**: Subsystem A shall satisfy: A_Advance shall move Step 1 to Step 2 and Step 2 to done only while not A_Paused.
- **R3**: Subsystem A shall satisfy: A_Pause shall suppress active step outputs without losing A_State; A_Resume clears A_Paused.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Abort shall return A_State to idle, suppress outputs, clear A_Paused, and latch A_Aborted.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Aborted only while A_Start, A_Advance, A_Pause, A_Resume, and A_Abort are all FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and B_Stage3Done returns idle with a one-scan B_Complete pulse.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Pause shall retain B_State while forcing every actuator FALSE; Done inputs while B_Paused shall not advance.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The active stage shall time out after 500 ms of unpaused execution and latch B_Fault.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Abort shall immediately return idle, force safe outputs, and latch B_Fault.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only in idle while B_Start, B_Abort, and every Done input are FALSE.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: At most one actuator may be TRUE, and B_Complete shall never coincide with an actuator.
- **R12** **[safety-critical]**: A TRUE A_Step1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- The runtime scan period is 100 ms.
- Pausing resets rather than accumulates the stage timeout.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

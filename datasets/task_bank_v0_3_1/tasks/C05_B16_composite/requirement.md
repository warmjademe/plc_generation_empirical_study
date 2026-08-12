# C05_B16_composite: Composed supervisory control: Heartbeat watchdog timeout -> Pre-lube motor lifecycle with feedback fault and cooldown

## Objective

Implement `C05_B16_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: While monitoring, a A_Heartbeat shall restart the 400 ms A_Watchdog interval.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Absence of A_Heartbeat for at least 400 ms shall latch A_TimedOut TRUE.
- **R3**: Subsystem A shall satisfy: A_Reset shall clear A_TimedOut only while A_MonitorEnable is FALSE.
- **R4**: Subsystem A shall satisfy: A_Healthy shall equal A_MonitorEnable and not A_TimedOut.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A permitted B_Start shall enter pre-lube with B_LubePump TRUE and B_MotorCommand FALSE.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_MotorCommand may B_Start only after B_OilPressure remains TRUE for 300 ms.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Failure to receive B_MotorFeedback within 400 ms of B_MotorCommand shall latch B_Fault and enter B_Cooldown.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_OilPressure loss while running shall immediately B_Stop the motor, latch B_Fault, and enter B_Cooldown.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop or B_Permit loss shall B_Stop B_MotorCommand and enter a 300 ms B_Cooldown with B_LubePump remaining TRUE.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Fault only in idle with B_Start FALSE; B_Cooldown completion returns idle without clearing B_Fault.
- **R11** **[safety-critical]**: A TRUE A_TimedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Heartbeat is a pulse lasting no more than one scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Start may remain TRUE through startup.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

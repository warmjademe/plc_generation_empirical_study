# C05_B11_composite: Composed supervisory control: Off-delay ventilation fan -> Heartbeat watchdog timeout

## Objective

Implement `C05_B11_composite` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Fan shall turn on without delay when A_Demand becomes TRUE and A_SafetyTrip is FALSE.
- **R2**: Subsystem A shall satisfy: After A_Demand becomes FALSE, A_Fan shall remain on for 300 ms unless A_SafetyTrip occurs.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_SafetyTrip shall turn A_Fan and A_RunOn off immediately.
- **R4**: Subsystem A shall satisfy: A_RunOn shall indicate the interval in which A_Demand is FALSE but the off-delay output remains TRUE.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While monitoring, a B_Heartbeat shall restart the 400 ms B_Watchdog interval.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Absence of B_Heartbeat for at least 400 ms shall latch B_TimedOut TRUE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_TimedOut only while B_MonitorEnable is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Healthy shall equal B_MonitorEnable and not B_TimedOut.
- **R9** **[safety-critical]**: A TRUE A_Fan shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Demand is held TRUE for at least one scan before an off-delay test.
- Each test starts from a fresh function-block instance.
- Heartbeat is a pulse lasting no more than one scan.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

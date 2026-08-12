# C09_B10_composite: Composed supervisory control: High and high-high alarm priority -> Delayed warning with trip lockout and acknowledgement

## Objective

Implement `C09_B10_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Value at or above A_HighLimit shall latch A_HighAlarm.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Value at or above A_HighHighLimit shall latch both alarms and A_Shutdown.
- **R3**: Subsystem A shall satisfy: A high alarm below A_HighHighLimit shall not by itself assert A_Shutdown.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear all latched outputs only below A_HighLimit.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_WarningCondition shall assert B_Warning only after it remains enabled for 300 ms.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TripCondition while enabled shall immediately latch B_Trip and B_LockedOut.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A newly asserted B_Warning or B_Trip shall set B_Unacked.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Acknowledge shall clear B_Unacked without clearing active B_Warning or latched B_Trip.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Trip and B_LockedOut only while both conditions and B_Enable are FALSE.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disabling the system shall clear the non-latched B_Warning but not an existing B_Trip.
- **R11** **[safety-critical]**: A TRUE A_HighAlarm shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_HighHighLimit is greater than A_HighLimit.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Acknowledge has priority over a new B_Unacked indication within the same scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

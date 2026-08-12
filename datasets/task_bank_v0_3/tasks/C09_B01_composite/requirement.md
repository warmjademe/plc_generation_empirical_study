# C09_B01_composite: Composed supervisory control: First-out fault recorder with deterministic priority -> Delayed warning with trip lockout and acknowledgement

## Objective

Implement `C09_B01_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_AnyFault shall equal the disjunction of all three fault inputs.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: The first observed fault shall latch A_LockedOut and its code in A_FirstFault.
- **R3**: Subsystem A shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R4**: Subsystem A shall satisfy: Later faults shall not overwrite A_FirstFault while A_LockedOut is TRUE.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut and A_FirstFault only when all fault inputs are FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_WarningCondition shall assert B_Warning only after it remains enabled for 300 ms.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TripCondition while enabled shall immediately latch B_Trip and B_LockedOut.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A newly asserted B_Warning or B_Trip shall set B_Unacked.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Acknowledge shall clear B_Unacked without clearing active B_Warning or latched B_Trip.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Trip and B_LockedOut only while both conditions and B_Enable are FALSE.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disabling the system shall clear the non-latched B_Warning but not an existing B_Trip.
- **R12** **[safety-critical]**: A TRUE A_AnyFault shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Acknowledge has priority over a new B_Unacked indication within the same scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

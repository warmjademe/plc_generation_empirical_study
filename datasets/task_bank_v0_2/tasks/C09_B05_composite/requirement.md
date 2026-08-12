# C09_B05_composite: Composed supervisory control: Delayed warning with trip lockout and acknowledgement -> First-out fault recorder with deterministic priority

## Objective

Implement `C09_B05_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_WarningCondition shall assert A_Warning only after it remains enabled for 300 ms.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_TripCondition while enabled shall immediately latch A_Trip and A_LockedOut.
- **R3**: Subsystem A shall satisfy: A newly asserted A_Warning or A_Trip shall set A_Unacked.
- **R4**: Subsystem A shall satisfy: A_Acknowledge shall clear A_Unacked without clearing active A_Warning or latched A_Trip.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Trip and A_LockedOut only while both conditions and A_Enable are FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: Disabling the system shall clear the non-latched A_Warning but not an existing A_Trip.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_AnyFault shall equal the disjunction of all three fault inputs.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The first observed fault shall latch B_LockedOut and its code in B_FirstFault.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Later faults shall not overwrite B_FirstFault while B_LockedOut is TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut and B_FirstFault only when all fault inputs are FALSE.
- **R12** **[safety-critical]**: A TRUE A_Warning shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Acknowledge has priority over a new Unacked indication within the same scan.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

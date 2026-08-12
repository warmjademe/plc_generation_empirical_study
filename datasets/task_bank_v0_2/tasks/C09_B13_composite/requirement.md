# C09_B13_composite: Composed supervisory control: Time-qualified sensor disagreement alarm -> First-out fault recorder with deterministic priority

## Objective

Implement `C09_B13_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds A_MaxDifference.
- **R2**: Subsystem A shall satisfy: A disagreement lasting 300 ms shall latch A_Alarm.
- **R3**: Subsystem A shall satisfy: A shorter disagreement shall not latch A_Alarm.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear A_Alarm only while no disagreement is present.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_AnyFault shall equal the disjunction of all three fault inputs.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The first observed fault shall latch B_LockedOut and its code in B_FirstFault.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Later faults shall not overwrite B_FirstFault while B_LockedOut is TRUE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut and B_FirstFault only when all fault inputs are FALSE.
- **R10** **[safety-critical]**: A TRUE A_Alarm shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- MaxDifference is non-negative.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

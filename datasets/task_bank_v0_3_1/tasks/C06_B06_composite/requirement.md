# C06_B06_composite: Composed supervisory control: Inspection-window reject lockout -> Configurable batch counter

## Objective

Implement `C06_B06_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Each rising A_Inspected edge shall add one to A_WindowCount and, when A_Rejected is TRUE, one to A_RejectCount.
- **R2**: Subsystem A shall satisfy: Completing A_WindowSize items shall pulse A_WindowComplete for one scan and then start a new zeroed window.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: If rejects in the completed window exceed A_RejectLimit, A_LockedOut shall latch TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: No new items shall be counted while A_LockedOut.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear counts, A_WindowComplete, and A_LockedOut.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_Item edge while B_Enable and below B_Target shall increment B_Count.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain between zero and B_Target.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_Count reaches B_Target.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count, B_BatchDone, and B_Accepted.
- **R10** **[safety-critical]**: A TRUE A_LockedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_WindowSize is at least 1 and A_RejectLimit is non-negative.
- Subsystem A: A_Rejected is sampled only on a rising A_Inspected edge.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_Target remains constant during a test and is between 1 and 100.
- Subsystem B: B_Item pulses are separated by at least one low scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

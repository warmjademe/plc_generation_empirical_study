# C06_B10_composite: Composed supervisory control: Configurable batch counter -> Inspection-window reject lockout

## Objective

Implement `C06_B10_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Only a rising A_Item edge while A_Enable and below A_Target shall increment A_Count.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall remain between zero and A_Target.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_Count reaches A_Target.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear A_Count, A_BatchDone, and A_Accepted.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Inspected edge shall add one to B_WindowCount and, when B_Rejected is TRUE, one to B_RejectCount.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Completing B_WindowSize items shall pulse B_WindowComplete for one scan and then start a new zeroed window.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If rejects in the completed window exceed B_RejectLimit, B_LockedOut shall latch TRUE.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: No new items shall be counted while B_LockedOut.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear counts, B_WindowComplete, and B_LockedOut.
- **R10** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Target remains constant during a test and is between 1 and 100.
- Item pulses are separated by at least one low scan.
- Each test starts from a fresh function-block instance.
- WindowSize is at least 1 and RejectLimit is non-negative.
- Rejected is sampled only on a rising Inspected edge.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

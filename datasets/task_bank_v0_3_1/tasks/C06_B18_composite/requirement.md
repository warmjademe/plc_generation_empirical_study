# C06_B18_composite: Composed supervisory control: Edge-counted batch with consecutive-reject lockout -> Inspection-window reject lockout

## Objective

Implement `C06_B18_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Only a rising A_ItemPulse while not stopped, A_Complete, or locked shall count one item.
- **R2**: Subsystem A shall satisfy: An accepted item increments A_AcceptedCount and clears A_ConsecutiveRejects; a A_Rejected item increments both reject counters.
- **R3**: Subsystem A shall satisfy: A_Complete shall latch when A_AcceptedCount reaches positive A_Target and no later item may change counts.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: Except for a qualified A_Reset scan, A_RejectLimit less than or equal to zero, or reaching A_RejectLimit consecutive rejects, shall latch A_LockedOut.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Stop has priority over A_ItemPulse and prevents every count change.
- **R6**: Subsystem A shall satisfy: A_Reset clears all state only while A_Stop is TRUE and A_ItemPulse is FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Inspected edge shall add one to B_WindowCount and, when B_Rejected is TRUE, one to B_RejectCount.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Completing B_WindowSize items shall pulse B_WindowComplete for one scan and then start a new zeroed window.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If rejects in the completed window exceed B_RejectLimit, B_LockedOut shall latch TRUE.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: No new items shall be counted while B_LockedOut.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear counts, B_WindowComplete, and B_LockedOut.
- **R12** **[safety-critical]**: A TRUE A_Complete shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem A: A_Target and A_RejectLimit remain constant during a test.
- Subsystem B: B_WindowSize is at least 1 and B_RejectLimit is non-negative.
- Subsystem B: B_Rejected is sampled only on a rising B_Inspected edge.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

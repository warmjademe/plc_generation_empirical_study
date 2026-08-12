# C06_W03_lean_composite: Composed supervisory control: Four-level alarm priority encoder -> Configurable batch counter

## Objective

Implement `C06_W03_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Emergency shall always produce A_Level 4 and A_Active TRUE, even when A_Suppress is TRUE.
- **R2**: Subsystem A shall satisfy: When not suppressed, the highest A_Active condition shall determine A_Level.
- **R3**: Subsystem A shall satisfy: A_Suppress shall force A_Level 0 and A_Active FALSE when A_Emergency is FALSE.
- **R4**: Subsystem A shall satisfy: A_Level 0 shall be equivalent to A_Active FALSE.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_Item edge while B_Enable and below B_Target shall increment B_Count.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain between zero and B_Target.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_Count reaches B_Target.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count, B_BatchDone, and B_Accepted.
- **R9** **[safety-critical]**: A TRUE A_Active shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_Target remains constant during a test and is between 1 and 100.
- Subsystem B: B_Item pulses are separated by at least one low scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_Target remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

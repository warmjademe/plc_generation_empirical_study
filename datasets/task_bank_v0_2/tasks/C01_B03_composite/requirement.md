# C01_B03_composite: Composed supervisory control: Four-level alarm priority encoder -> Mode-dependent command selection

## Objective

Implement `C01_B03_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Emergency shall always produce A_Level 4 and A_Active TRUE, even when A_Suppress is TRUE.
- **R2**: Subsystem A shall satisfy: When not suppressed, the highest A_Active condition shall determine A_Level.
- **R3**: Subsystem A shall satisfy: A_Suppress shall force A_Level 0 and A_Active FALSE when A_Emergency is FALSE.
- **R4**: Subsystem A shall satisfy: A_Level 0 shall be equivalent to A_Active FALSE.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Command shall follow B_AutoDemand in automatic mode and B_ManualDemand in manual mode, but only when B_SafetyOK is TRUE and B_Inhibit is FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or B_Inhibit is TRUE.
- **R7** **[safety-critical]**: A TRUE A_Active shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R8** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R9**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R10** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

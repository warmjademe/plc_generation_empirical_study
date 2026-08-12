# C04_R01_lean_composite: Composed supervisory control: Qualified event capture with saturation -> Four-level alarm priority encoder

## Objective

Implement `C04_R01_lean_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Reset shall clear A_Count and A_AcceptedPulse.
- **R2**: Subsystem A shall satisfy: Only a rising A_Event edge with A_Qualify TRUE and A_Count below A_MaxCount shall increment A_Count.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall not exceed A_MaxCount.
- **R4**: Subsystem A shall satisfy: A_AtLimit shall be TRUE exactly when A_Count is at least A_MaxCount.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Emergency shall always produce B_Level 4 and B_Active TRUE, even when B_Suppress is TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When not suppressed, the highest B_Active condition shall determine B_Level.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Suppress shall force B_Level 0 and B_Active FALSE when B_Emergency is FALSE.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Level 0 shall be equivalent to B_Active FALSE.
- **R9** **[safety-critical]**: A TRUE A_AcceptedPulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_MaxCount is constant during a test and is at least 1.
- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

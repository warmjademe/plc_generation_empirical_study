# C04_B04_composite: Composed supervisory control: Qualified event capture with saturation -> Qualified dual-edge recorder with saturation and re-arm

## Objective

Implement `C04_B04_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Reset shall clear A_Count and A_AcceptedPulse.
- **R2**: Subsystem A shall satisfy: Only a rising A_Event edge with A_Qualify TRUE and A_Count below A_MaxCount shall increment A_Count.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall not exceed A_MaxCount.
- **R4**: Subsystem A shall satisfy: A_AtLimit shall be TRUE exactly when A_Count is at least A_MaxCount.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a qualified, non-inhibited rising edge observed while not previously B_Locked may be accepted.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous eligible edges shall accept A only.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each accepted event increments B_Count once and records B_LastSource.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Except for a qualified B_Reset scan, B_Count shall saturate at B_MaxCount and latch B_Locked; B_MaxCount less than or equal to zero locks without counting.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A held-high event shall not retrigger until observed low and then rising again.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Count, B_Locked, and B_LastSource only while both events are low.
- **R11** **[safety-critical]**: A TRUE A_AcceptedPulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_MaxCount is constant during a test and is at least 1.
- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem B: B_MaxCount remains constant during a test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

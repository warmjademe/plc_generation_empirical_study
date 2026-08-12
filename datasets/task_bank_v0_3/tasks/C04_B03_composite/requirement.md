# C04_B03_composite: Composed supervisory control: Qualified event capture with saturation -> Toggle output on qualified rising edge

## Objective

Implement `C04_B03_composite` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Reset shall clear A_Count and A_AcceptedPulse.
- **R2**: Subsystem A shall satisfy: Only a rising A_Event edge with A_Qualify TRUE and A_Count below A_MaxCount shall increment A_Count.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall not exceed A_MaxCount.
- **R4**: Subsystem A shall satisfy: A_AtLimit shall be TRUE exactly when A_Count is at least A_MaxCount.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_State and suppress B_AcceptedPulse with highest priority.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A rising B_Button edge while B_Enable is TRUE shall invert B_State exactly once.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Holding B_Button TRUE shall not repeatedly toggle B_State.
- **R8** **[safety-critical]**: A TRUE A_AcceptedPulse shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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

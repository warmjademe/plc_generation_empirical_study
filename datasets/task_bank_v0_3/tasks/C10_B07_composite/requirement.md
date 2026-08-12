# C10_B07_composite: Composed supervisory control: Fair two-client resource arbiter with emergency lockout -> Lead-lag pump demand control

## Objective

Implement `C10_B07_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_GrantA and A_GrantB shall never be TRUE simultaneously.
- **R2**: Subsystem A shall satisfy: When idle, a single request shall receive the resource; simultaneous requests shall follow A_Turn.
- **R3**: Subsystem A shall satisfy: A_Done shall release the resource before a new owner is selected on a later scan.
- **R4**: Subsystem A shall satisfy: After A completes A_Turn shall prefer B, and after B completes A_Turn shall prefer A.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Emergency shall immediately revoke all grants and latch A_LockedOut.
- **R6**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut only while A_Emergency and both requests are FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: With B_LowDemand only, the available selected lead pump shall run and the lag pump shall remain off.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: With B_HighDemand, every available pump shall run.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If the selected lead is unavailable under B_LowDemand, the available lag pump shall run.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: No pump shall run when neither demand input is TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_CapacityShortfall shall indicate zero available pumps for B_LowDemand or fewer than two for B_HighDemand.
- **R12** **[safety-critical]**: A TRUE A_GrantA shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

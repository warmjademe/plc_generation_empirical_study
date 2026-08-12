# C10_B18_composite: Composed supervisory control: Three-pump staged dispatch with lead preference and feedback exclusion -> Fair two-client resource arbiter with emergency lockout

## Objective

Implement `C10_B18_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_LowDemand shall request one pump and A_HighDemand shall request two, with A_HighDemand taking priority.
- **R2**: Subsystem A shall satisfy: Dispatch shall prefer A_Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch A_Fault.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall immediately clear every run command; A_Reset clears failures only while both demand inputs and A_Stop are FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_GrantA and B_GrantB shall never be TRUE simultaneously.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When idle, a single request shall receive the resource; simultaneous requests shall follow B_Turn.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Done shall release the resource before a new owner is selected on a later scan.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After A completes B_Turn shall prefer B, and after B completes B_Turn shall prefer A.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Emergency shall immediately revoke all grants and latch B_LockedOut.
- **R12**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut only while B_Emergency and both requests are FALSE.
- **R13** **[safety-critical]**: A TRUE A_Run2 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: At most two pumps are required simultaneously.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

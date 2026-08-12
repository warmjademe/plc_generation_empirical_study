# C10_B08_composite: Composed supervisory control: Fair two-client resource arbiter with emergency lockout -> Three-pump staged dispatch with lead preference and feedback exclusion

## Objective

Implement `C10_B08_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_GrantA and A_GrantB shall never be TRUE simultaneously.
- **R2**: Subsystem A shall satisfy: When idle, a single request shall receive the resource; simultaneous requests shall follow A_Turn.
- **R3**: Subsystem A shall satisfy: A_Done shall release the resource before a new owner is selected on a later scan.
- **R4**: Subsystem A shall satisfy: After A completes A_Turn shall prefer B, and after B completes A_Turn shall prefer A.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Emergency shall immediately revoke all grants and latch A_LockedOut.
- **R6**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut only while A_Emergency and both requests are FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_LowDemand shall request one pump and B_HighDemand shall request two, with B_HighDemand taking priority.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Dispatch shall prefer B_Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch B_Fault.
- **R12** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall immediately clear every run command; B_Reset clears failures only while both demand inputs and B_Stop are FALSE.
- **R13** **[safety-critical]**: A TRUE A_GrantA shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: At most two pumps are required simultaneously.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# C10_B04_composite: Composed supervisory control: Duty-standby pump feedback failover -> Three-pump staged dispatch with lead preference and feedback exclusion

## Objective

Implement `C10_B04_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A new A_Demand shall command the available duty pump, or the standby if the duty pump is unavailable.
- **R2**: Subsystem A shall satisfy: If the commanded pump lacks feedback for 300 ms, control shall transfer to an available standby pump.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Both run commands shall never be TRUE simultaneously.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Failure shall latch if A_Demand cannot be served by an available pump with feedback after failover.
- **R5**: Subsystem A shall satisfy: A_Demand FALSE shall stop both pumps; A_Reset may clear A_Failure only with A_Demand FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_LowDemand shall request one pump and B_HighDemand shall request two, with B_HighDemand taking priority.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Dispatch shall prefer B_Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch B_Fault.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop shall immediately clear every run command; B_Reset clears failures only while both demand inputs and B_Stop are FALSE.
- **R12** **[safety-critical]**: A TRUE A_Pump1Run shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: Pump feedback is sampled at scan start.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: At most two pumps are required simultaneously.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

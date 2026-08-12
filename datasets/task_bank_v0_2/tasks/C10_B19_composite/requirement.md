# C10_B19_composite: Composed supervisory control: Three-pump staged dispatch with lead preference and feedback exclusion -> Alternating two-pump starts

## Objective

Implement `C10_B19_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_LowDemand shall request one pump and A_HighDemand shall request two, with A_HighDemand taking priority.
- **R2**: Subsystem A shall satisfy: Dispatch shall prefer A_Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.
- **R5** **[safety-critical]**: Subsystem A shall satisfy: A_Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch A_Fault.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_Stop shall immediately clear every run command; A_Reset clears failures only while both demand inputs and A_Stop are FALSE.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Demand shall start at most one available pump.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both pumps are available, successive B_Demand episodes shall alternate the selected pump.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If the preferred pump is B_Unavailable, the other available pump shall run.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Unavailable shall be TRUE exactly when B_Demand is TRUE and neither pump is available.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset without B_Demand shall set B_NextPump to 1 and stop both pumps.
- **R12** **[safety-critical]**: A TRUE A_Run1 shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- At most two pumps are required simultaneously.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.

# IEC-ST Core v1

IEC-ST Core v1 is a benchmark profile, not a claim of complete IEC 61131-3
conformance.  It defines the common language and execution assumptions against which
the reference programs and generated candidates are evaluated.

## Program unit

- Each task requests one `FUNCTION_BLOCK`.
- The function-block name and its `VAR_INPUT` and `VAR_OUTPUT` declarations are
  fixed by `interface.st`.
- A harness instantiates the block and calls it exactly once per scan.
- Physical I/O addresses, resources, tasks, vendor project files, communication
  protocols, and hardware configuration are outside the profile.

## Included constructs

- `FUNCTION_BLOCK`, `VAR_INPUT`, `VAR_OUTPUT`, `VAR`, `END_VAR`
- scalar `BOOL`, `INT`, `DINT`, `REAL`, and `TIME`
- declarations with explicit scalar initial values
- assignment, parentheses, arithmetic, comparison, and Boolean operators
- `IF`/`ELSIF`/`ELSE`, `CASE`, and statically bounded `FOR`
- standard conversion functions used by the reference programs
- state retained in function-block variables across scans
- `TON`, `TOF`, `TP`, `CTU`, `CTD`, `R_TRIG`, and `F_TRIG` where a task declares
  the block explicitly

## Excluded constructs

- vendor namespaces, pragmas, attributes, addresses, libraries, and extensions
- pointers, references, dynamic allocation, and recursion
- unbounded loops and loops whose bound depends on a runtime input
- strings, dates, user-defined structures, unions, inheritance, and interfaces
- hardware I/O mapping, network communication, motion control, and safety-certified
  library blocks
- graphical-language serialization and PLCopen XML

## Scan semantics

- Inputs are sampled at the beginning of a scan.
- The function block executes once.
- Outputs and retained variables are observed at the end of the scan.
- Tests start from a fresh function-block instance unless the case states otherwise.
- The nominal scan period is task metadata.  Timer tasks use a scan period of 100 ms.
- Dynamic timer assertions allow the explicitly declared tolerance in the test file;
  no implicit wall-clock tolerance is permitted.

## Boolean and arithmetic semantics

- Boolean operators must be parenthesized when mixed, avoiding reliance on unclear
  precedence.
- Integer division, overflow, and conversion are tested only where the expected
  behavior is explicitly stated.
- REAL comparisons in dynamic tests use the task's absolute tolerance.

## Tool qualification rule

A construct remains in IEC-ST Core v1 only after the conformance suite demonstrates
that the pinned MatIEC, RuSTy, and OpenPLC configurations either agree on it or that
the benchmark supplies a documented compatibility transformation.  A tool
disagreement is an infrastructure finding and is not silently scored as a model
failure.

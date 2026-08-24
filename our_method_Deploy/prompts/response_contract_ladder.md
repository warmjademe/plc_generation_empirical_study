Return exactly one JSON object with this envelope and no Markdown fence:

{
  "repair_hypothesis": "one concise, testable repair hypothesis",
  "target_requirements": ["R1", "R2"],
  "ladder_program": {
    "schema_version": "1.0",
    "function_block": "the exact supplied FUNCTION_BLOCK name",
    "locals": [
      {"name": "RunLatch", "type": "BOOL", "initial": false}
    ],
    "rungs": [
      {
        "id": "RUNG_01",
        "comment": "concise Chinese explanation",
        "condition": {"op": "var", "name": "StartButton"},
        "instructions": [
          {"type": "coil","target": "RunLatch", "mode": "set"}
        ]
      }
    ]
  }
}

The only ladder_program keys are schema_version, function_block, locals, and
rungs. The only supported local type is BOOL. Do not repeat VAR_INPUT or
VAR_OUTPUT in locals; the harness inserts the fixed interface.

Every condition is an expression object. Supported expressions are:

- {"op":"var","name":"X"}
- {"op":"not","arg":EXPR}
- {"op":"and|or","args":[EXPR,EXPR,...]}

NOT may wrap only a direct var expression. This is the calibrated ISPSoft
native-LD contact subset.

Supported instructions are:

- {"type":"coil","target":"BoolName","mode":"normal|set|reset"}

Rungs are ordered. Put a higher-priority reset after a lower-priority set. Use
a normal coil only for combinational outputs and exactly once per target. Use
set/reset coils for retained state. Every rung must have a unique IEC
identifier, a BOOL condition, at least one instruction, and a concise Chinese
comment. All expression operands and coil targets must be BOOL. Do not emit
physical addresses, ST, SVG, prose, or any unsupported construct.

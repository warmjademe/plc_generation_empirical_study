Return exactly this tagged format:

<repair_hypothesis>one concise, testable repair hypothesis</repair_hypothesis>
<target_requirements>comma-separated requirement IDs, or NONE</target_requirements>
<ladder_program>
{
  "schema_version": "1.0",
  "function_block": "the exact supplied FUNCTION_BLOCK name",
  "locals": [
    {"name": "RunLatch", "type": "BOOL", "initial": false},
    {"name": "DelayScans", "type": "INT", "initial": 0}
  ],
  "rungs": [
    {
      "id": "RUNG_01",
      "comment": "concise Chinese explanation",
      "condition": {"op": "var", "name": "StartButton"},
      "instructions": [
        {"type": "coil", "target": "RunLatch", "mode": "set"}
      ]
    }
  ]
}
</ladder_program>

The only top-level keys are schema_version, function_block, locals, and rungs.
Supported local types are BOOL, INT, DINT, and REAL. Do not repeat VAR_INPUT or
VAR_OUTPUT in locals; the harness inserts the fixed interface.

Every condition and instruction value is an expression object. Supported
expressions are:

- {"op":"var","name":"X"}
- {"op":"const","type":"BOOL|INT|DINT|REAL","value":...}
- {"op":"not","arg":EXPR}
- {"op":"and|or|xor","args":[EXPR,EXPR,...]}
- {"op":"compare","operator":"EQ|NE|LT|LE|GT|GE","left":EXPR,"right":EXPR}
- {"op":"arithmetic","operator":"ADD|SUB|MUL","left":EXPR,"right":EXPR}

Supported instructions are:

- {"type":"coil","target":"BoolName","mode":"normal|set|reset"}
- {"type":"assign","target":"Name","value":EXPR}
- {"type":"increment_saturating","target":"IntName","limit":POSITIVE_INTEGER}

Rungs are ordered. Put a higher-priority reset after a lower-priority set. Use
a normal coil only for combinational outputs and exactly once per target. Use
set/reset coils or conditional assign instructions for retained state. Every
rung must have a unique IEC identifier, a BOOL condition, at least one
instruction, and a concise Chinese comment. Return valid JSON with no comments
inside the JSON document.

The operands of and/or/xor/not must be BOOL; arithmetic operands must be
numeric. Do not add or multiply BOOL values to encode a priority. For a numeric
priority encoder, first assign the default value under a TRUE condition, then
add conditional assign rungs from the lowest priority to the highest priority.
Because later rungs execute later, the highest active condition deterministically
overwrites the lower level. Compute a related BOOL output in one separate normal
coil rung after the numeric priority rungs.

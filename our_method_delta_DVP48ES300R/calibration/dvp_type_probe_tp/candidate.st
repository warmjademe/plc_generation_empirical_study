FUNCTION_BLOCK DVP_TYPE_PROBE_TP
VAR_INPUT
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Active : BOOL;
END_VAR
VAR
    ProbeTimer : TP;
END_VAR
ProbeTimer(IN := Enable, PT := T#100ms);
Active := Enable;
END_FUNCTION_BLOCK

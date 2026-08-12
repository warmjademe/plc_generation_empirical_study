FUNCTION_BLOCK C01_E01_two_input_permissive
VAR_INPUT
    Enable : BOOL;
    GuardClosed : BOOL;
END_VAR
VAR_OUTPUT
    RunPermit : BOOL;
END_VAR

RunPermit := Enable AND GuardClosed;

END_FUNCTION_BLOCK

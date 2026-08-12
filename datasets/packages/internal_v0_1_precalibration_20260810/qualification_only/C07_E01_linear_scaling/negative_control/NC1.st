FUNCTION_BLOCK C08_E01_linear_scaling
VAR_INPUT
    Raw : INT;
END_VAR
VAR_OUTPUT
    Engineering : REAL;
END_VAR

Engineering := INT_TO_REAL(Raw) * 0.1;

END_FUNCTION_BLOCK

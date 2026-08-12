FUNCTION_BLOCK C07_H02_rate_of_change_trip
VAR_INPUT
    Value : REAL;
    Enable : BOOL;
    MaxRise : REAL;
    MaxFall : REAL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Delta : REAL;
    Trip : BOOL;
    Ready : BOOL;
END_VAR
END_FUNCTION_BLOCK

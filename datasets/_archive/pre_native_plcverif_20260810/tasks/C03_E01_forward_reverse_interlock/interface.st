FUNCTION_BLOCK C03_E01_forward_reverse_interlock
VAR_INPUT
    ForwardRequest : BOOL;
    ReverseRequest : BOOL;
    Permit : BOOL;
END_VAR
VAR_OUTPUT
    Forward : BOOL;
    Reverse : BOOL;
END_VAR
END_FUNCTION_BLOCK

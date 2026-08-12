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

Forward := Permit OR ForwardRequest AND (NOT ReverseRequest);
Reverse := Permit AND ReverseRequest AND (NOT ForwardRequest);

END_FUNCTION_BLOCK

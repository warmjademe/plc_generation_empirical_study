FUNCTION_BLOCK C01_H02_redundant_channel_gate
VAR_INPUT
    ChA : BOOL;
    ChB : BOOL;
    TestMode : BOOL;
    TestPermit : BOOL;
    ProcessRequest : BOOL;
END_VAR
VAR_OUTPUT
    SafeEnable : BOOL;
    Disagree : BOOL;
    TestActive : BOOL;
END_VAR
END_FUNCTION_BLOCK

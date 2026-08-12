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

Disagree := ChA <> ChB;
TestActive := TestMode AND TestPermit;
IF TestMode THEN
    SafeEnable := ProcessRequest AND TestPermit AND ChA;
ELSE
    SafeEnable := ProcessRequest AND ChA AND ChB;
END_IF;

END_FUNCTION_BLOCK

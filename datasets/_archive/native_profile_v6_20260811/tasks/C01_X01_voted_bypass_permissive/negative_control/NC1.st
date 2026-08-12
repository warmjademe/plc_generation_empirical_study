FUNCTION_BLOCK C01_X01_voted_bypass_permissive
VAR_INPUT
    Ch1 : BOOL;
    Ch2 : BOOL;
    Ch3 : BOOL;
    AutoMode : BOOL;
    AutoRequest : BOOL;
    ManualRequest : BOOL;
    BypassRequest : BOOL;
    BypassPermit : BOOL;
    SafetyOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    RunPermit : BOOL;
    Degraded : BOOL;
    BypassActive : BOOL;
    Blocked : BOOL;
END_VAR
VAR
    SelectedRequest : BOOL;
    VoteOK : BOOL;
    AnyChannel : BOOL;
    Unanimous : BOOL;
END_VAR

SelectedRequest := (AutoMode AND AutoRequest) OR ((NOT AutoMode) AND ManualRequest);
VoteOK := (Ch1 AND Ch2) OR (Ch1 AND Ch3) OR (Ch2 AND Ch3);
AnyChannel := Ch1 OR Ch2 OR Ch3;
Unanimous := (Ch1 AND Ch2 AND Ch3) OR ((NOT Ch1) AND (NOT Ch2) AND (NOT Ch3));
IF Reset AND (NOT AutoRequest) AND (NOT ManualRequest) THEN
    BypassActive := FALSE;
ELSIF (NOT AutoMode) AND BypassRequest AND BypassPermit AND SafetyOK AND AnyChannel THEN
    BypassActive := FALSE;
END_IF;
RunPermit := SelectedRequest AND SafetyOK AND (VoteOK OR BypassActive);
Degraded := RunPermit AND ((NOT Unanimous) OR BypassActive);
Blocked := SelectedRequest AND (NOT RunPermit);

END_FUNCTION_BLOCK

FUNCTION_BLOCK C03_B04_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_Stop : BOOL;
    A_C1Clear : BOOL;
    A_C2Clear : BOOL;
    A_C3Clear : BOOL;
    A_C2Available : BOOL;
    A_C3Available : BOOL;
    B_HeatRequest : BOOL;
    B_Stop : BOOL;
    B_GuardClosed : BOOL;
    B_DamperOpen : BOOL;
    B_AirflowOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_C1Run : BOOL;
    A_C2Run : BOOL;
    A_C3Run : BOOL;
    A_Blocked : BOOL;
    B_DamperCommand : BOOL;
    B_FanCommand : BOOL;
    B_HeaterCommand : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_ProofStable : TON;
    B_ProofTimeout : TON;
END_VAR

A_C3Run := A_RunRequest AND A_C3Available AND A_C3Clear AND (NOT A_Stop);
A_C2Run := A_C3Run AND A_C2Available AND A_C2Clear;
A_C1Run := A_C2Run AND A_C1Clear;
A_Blocked := A_RunRequest AND ((NOT A_C1Clear) OR (NOT A_C2Clear) OR (NOT A_C3Clear)
           OR (NOT A_C2Available) OR (NOT A_C3Available));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_C1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_ProofStable(IN := (B_State = 1) AND B_DamperOpen AND B_AirflowOK, PT := T#300ms);
    B_ProofTimeout(IN := (B_State = 1) AND ((NOT B_DamperOpen) OR (NOT B_AirflowOK)), PT := T#600ms);
    IF B_Stop OR (NOT B_GuardClosed) THEN
        IF (B_State = 2) AND (NOT B_GuardClosed) THEN B_Fault := TRUE; END_IF;
        B_State := 0;
    ELSIF (B_State = 2) AND ((NOT B_DamperOpen) OR (NOT B_AirflowOK)) THEN
        B_Fault := TRUE;
        B_State := 0;
    ELSIF B_ProofTimeout.Q THEN
        B_Fault := TRUE;
        B_State := 0;
    ELSIF (B_State = 0) AND B_HeatRequest AND B_GuardClosed AND (NOT B_Fault) THEN
        B_State := 1;
    ELSIF (B_State = 1) AND B_ProofStable.Q THEN
        B_State := 2;
    ELSIF (B_State = 2) AND (NOT B_HeatRequest) THEN
        B_State := 0;
    END_IF;
    IF B_Reset AND (B_State = 0) AND (NOT B_HeatRequest) THEN B_Fault := FALSE; END_IF;
    B_DamperCommand := ((B_State = 1) OR (B_State = 2)) AND (NOT B_Fault);
    B_FanCommand := ((B_State = 1) OR (B_State = 2)) AND (NOT B_Fault);
    B_HeaterCommand := (B_State = 2) AND (NOT B_Fault);
ELSE
    B_DamperCommand := FALSE;
    B_FanCommand := FALSE;
    B_HeaterCommand := FALSE;
    B_Fault := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK

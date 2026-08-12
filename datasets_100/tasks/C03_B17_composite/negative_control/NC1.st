FUNCTION_BLOCK C03_B17_composite
VAR_INPUT
    A_HeatRequest : BOOL;
    A_Stop : BOOL;
    A_GuardClosed : BOOL;
    A_DamperOpen : BOOL;
    A_AirflowOK : BOOL;
    A_Reset : BOOL;
    B_RunRequest : BOOL;
    B_Stop : BOOL;
    B_C1Clear : BOOL;
    B_C2Clear : BOOL;
    B_C3Clear : BOOL;
    B_C2Available : BOOL;
    B_C3Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_DamperCommand : BOOL;
    A_FanCommand : BOOL;
    A_HeaterCommand : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_C1Run : BOOL;
    B_C2Run : BOOL;
    B_C3Run : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_ProofStable : TON;
    A_ProofTimeout : TON;
END_VAR

A_ProofStable(IN := (A_State = 1) AND A_DamperOpen AND A_AirflowOK, PT := T#300ms);
A_ProofTimeout(IN := (A_State = 1) AND ((NOT A_DamperOpen) OR (NOT A_AirflowOK)), PT := T#600ms);
IF A_Stop OR (NOT A_GuardClosed) THEN
    IF (A_State = 2) AND (NOT A_GuardClosed) THEN A_Fault := TRUE; END_IF;
    A_State := 0;
ELSIF (A_State = 2) AND ((NOT A_DamperOpen) OR (NOT A_AirflowOK)) THEN
    A_Fault := TRUE;
    A_State := 0;
ELSIF A_ProofTimeout.Q THEN
    A_Fault := TRUE;
    A_State := 0;
ELSIF (A_State = 0) AND A_HeatRequest AND A_GuardClosed AND (NOT A_Fault) THEN
    A_State := 1;
ELSIF (A_State = 1) AND A_ProofStable.Q THEN
    A_State := 2;
ELSIF (A_State = 2) AND (NOT A_HeatRequest) THEN
    A_State := 0;
END_IF;
IF A_Reset AND (A_State = 0) AND (NOT A_HeatRequest) THEN A_Fault := FALSE; END_IF;
A_DamperCommand := ((A_State = 1) OR (A_State = 2)) AND (NOT A_Fault);
A_FanCommand := ((A_State = 1) OR (A_State = 2)) AND (NOT A_Fault);
A_HeaterCommand := (A_State = 2) AND (NOT A_Fault);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_DamperCommand THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_C3Run := B_RunRequest AND B_C3Available AND B_C3Clear AND (NOT B_Stop);
    B_C2Run := B_C3Run AND B_C2Available AND B_C2Clear;
    B_C1Run := B_C2Run AND B_C1Clear;
    B_Blocked := B_RunRequest AND ((NOT B_C1Clear) OR (NOT B_C2Clear) OR (NOT B_C3Clear)
               OR (NOT B_C2Available) OR (NOT B_C3Available));
ELSE
    B_C1Run := FALSE;
    B_C2Run := FALSE;
    B_C3Run := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK

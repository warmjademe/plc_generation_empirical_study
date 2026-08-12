FUNCTION_BLOCK C03_B16_composite
VAR_INPUT
    A_Temperature : REAL;
    A_Setpoint : REAL;
    A_Enable : BOOL;
    A_SafetyTrip : BOOL;
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
    A_Heat : BOOL;
    A_Cool : BOOL;
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

A_Heat := FALSE;
A_Cool := FALSE;
IF A_Enable AND (NOT A_SafetyTrip) THEN
    IF A_Temperature < (A_Setpoint - 1.0) THEN
        A_Heat := FALSE;
    ELSIF A_Temperature > (A_Setpoint + 1.0) THEN
        A_Cool := TRUE;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heat THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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

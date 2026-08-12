FUNCTION_BLOCK C03_B19_composite
VAR_INPUT
    A_HeatRequest : BOOL;
    A_Stop : BOOL;
    A_GuardClosed : BOOL;
    A_DamperOpen : BOOL;
    A_AirflowOK : BOOL;
    A_Reset : BOOL;
    B_RunRequest : BOOL;
    B_TankLevelOK : BOOL;
    B_ValveFeedbackOpen : BOOL;
    B_PumpFeedback : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_DamperCommand : BOOL;
    A_FanCommand : BOOL;
    A_HeaterCommand : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_ValveCommand : BOOL;
    B_PumpCommand : BOOL;
    B_InterlockAlarm : BOOL;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_ValveCommand := B_RunRequest AND B_TankLevelOK AND (NOT B_Stop);
    B_PumpCommand := B_ValveCommand AND B_ValveFeedbackOpen;
    B_InterlockAlarm := B_PumpFeedback AND (NOT B_ValveFeedbackOpen);
ELSE
    B_ValveCommand := FALSE;
    B_PumpCommand := FALSE;
    B_InterlockAlarm := FALSE;
END_IF;

END_FUNCTION_BLOCK

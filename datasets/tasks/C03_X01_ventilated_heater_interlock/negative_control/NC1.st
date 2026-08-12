FUNCTION_BLOCK C03_X01_ventilated_heater_interlock
VAR_INPUT
    HeatRequest : BOOL;
    Stop : BOOL;
    GuardClosed : BOOL;
    DamperOpen : BOOL;
    AirflowOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    DamperCommand : BOOL;
    FanCommand : BOOL;
    HeaterCommand : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
VAR
    ProofStable : TON;
    ProofTimeout : TON;
END_VAR

ProofStable(IN := (State = 1) AND DamperOpen AND AirflowOK, PT := T#300ms);
ProofTimeout(IN := (State = 1) AND ((NOT DamperOpen) OR (NOT AirflowOK)), PT := T#600ms);
IF Stop OR (NOT GuardClosed) THEN
    IF (State = 2) AND (NOT GuardClosed) THEN Fault := TRUE; END_IF;
    State := 0;
ELSIF (State = 2) AND ((NOT DamperOpen) OR (NOT AirflowOK)) THEN
    Fault := TRUE;
    State := 0;
ELSIF ProofTimeout.Q THEN
    Fault := TRUE;
    State := 0;
ELSIF (State = 0) AND HeatRequest AND GuardClosed AND (NOT Fault) THEN
    State := 1;
ELSIF (State = 1) AND ProofStable.Q THEN
    State := 2;
ELSIF (State = 2) AND (NOT HeatRequest) THEN
    State := 0;
END_IF;
IF Reset AND (State = 0) AND (NOT HeatRequest) THEN Fault := FALSE; END_IF;
DamperCommand := ((State = 1) OR (State = 2)) AND (NOT Fault);
FanCommand := ((State = 1) OR (State = 2)) AND (NOT Fault);
HeaterCommand := (State = 2) AND (NOT Fault);

(* seeded fault: force HeaterCommand *)
HeaterCommand := FALSE;
END_FUNCTION_BLOCK

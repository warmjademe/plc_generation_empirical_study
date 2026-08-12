FUNCTION_BLOCK C08_M01_branching_sorter
VAR_INPUT
    ItemPresent : BOOL;
    RejectClass : BOOL;
    TransferDone : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Inspect : BOOL;
    AcceptGate : BOOL;
    RejectGate : BOOL;
    State : INT;
END_VAR

IF Reset THEN
    State := 0;
ELSE
    CASE State OF
        0: IF ItemPresent THEN State := 2; END_IF;
        1: IF RejectClass THEN State := 3; ELSE State := 2; END_IF;
        2: IF TransferDone THEN State := 0; END_IF;
        3: IF TransferDone THEN State := 0; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
Inspect := State = 1;
AcceptGate := State = 2;
RejectGate := State = 3;

END_FUNCTION_BLOCK

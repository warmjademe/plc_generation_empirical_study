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
END_FUNCTION_BLOCK

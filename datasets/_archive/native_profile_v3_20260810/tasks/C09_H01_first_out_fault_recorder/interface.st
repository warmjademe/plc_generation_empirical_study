FUNCTION_BLOCK C09_H01_first_out_fault_recorder
VAR_INPUT
    FaultA : BOOL;
    FaultB : BOOL;
    FaultC : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    AnyFault : BOOL;
    LockedOut : BOOL;
    FirstFault : INT;
END_VAR
END_FUNCTION_BLOCK

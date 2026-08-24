FUNCTION_BLOCK C01_B02_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    CrossLatch : BOOL := FALSE;
END_VAR
(* LD RUNG_01: 默认A_Level为0，A_Active为假（R4） *)
IF TRUE THEN
    A_Level := 0;
END_IF;
IF TRUE THEN
    A_Active := FALSE;
END_IF;
(* LD RUNG_02: A_Info且未抑制时置A_Level为1（R2） *)
IF (A_Info) AND (NOT (A_Suppress)) THEN
    A_Level := 1;
END_IF;
(* LD RUNG_03: A_Warning且未抑制时置A_Level为2（R2） *)
IF (A_Warning) AND (NOT (A_Suppress)) THEN
    A_Level := 2;
END_IF;
(* LD RUNG_04: A_Trip且未抑制时置A_Level为3（R2） *)
IF (A_Trip) AND (NOT (A_Suppress)) THEN
    A_Level := 3;
END_IF;
(* LD RUNG_05: A_Emergency无条件置A_Level为4且A_Active为真（R1） *)
IF A_Emergency THEN
    A_Level := 4;
END_IF;
IF A_Emergency THEN
    A_Active := TRUE;
END_IF;
(* LD RUNG_06: 未被抑制且非紧急时按电平确定A_Active（R3） *)
IF (NOT (A_Suppress)) AND (NOT (A_Emergency)) AND ((A_Level) > (0)) THEN
    A_Active := TRUE;
END_IF;
(* LD RUNG_07: A_Active置位CrossLatch锁存（R7） *)
IF A_Active THEN
    CrossLatch := TRUE;
END_IF;
(* LD RUNG_08: CrossReset优先复位并封锁子系统B（R8） *)
IF CrossReset THEN
    CrossLatch := FALSE;
END_IF;
(* LD RUNG_09: 输出CrossReady为锁存值（R9） *)
IF TRUE THEN
    CrossReady := CrossLatch;
END_IF;
(* LD RUNG_10: 未使能或未就绪时B输出为默认（R8） *)
IF (NOT (SubsystemBEnable)) OR (NOT (CrossReady)) THEN
    B_Vote := FALSE;
END_IF;
IF (NOT (SubsystemBEnable)) OR (NOT (CrossReady)) THEN
    B_Unanimous := FALSE;
END_IF;
(* LD RUNG_11: 使能且就绪时二取一表决（R5） *)
IF (SubsystemBEnable) AND (CrossReady) THEN
    B_Vote := ((B_S1) AND (B_S2)) OR ((B_S1) AND (B_S3)) OR ((B_S2) AND (B_S3));
END_IF;
(* LD RUNG_12: 使能且就绪时三通道一致判断（R6） *)
IF (SubsystemBEnable) AND (CrossReady) THEN
    B_Unanimous := ((B_S1) AND (B_S2) AND (B_S3)) OR ((NOT (B_S1)) AND (NOT (B_S2)) AND (NOT (B_S3)));
END_IF;
(* LD RUNG_13: CrossBlocked指示使能未就绪（R10） *)
CrossBlocked := (SubsystemBEnable) AND (NOT (CrossReady));
END_FUNCTION_BLOCK

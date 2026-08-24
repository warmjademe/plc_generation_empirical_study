(*
    功能块名称：SMOKE_MOTOR
    功能说明：根据启动与停止信号生成电机运行命令。
    扫描语义：PLC 在每个扫描周期读取一次输入，并在本周期结束时更新 Motor。
*)
FUNCTION_BLOCK SMOKE_MOTOR
VAR_INPUT
    Start : BOOL; (* 启动请求；TRUE 表示本扫描周期请求电机运行。 *)
    Stop : BOOL;  (* 停止请求；TRUE 表示必须停止，优先级高于 Start。 *)
END_VAR
VAR_OUTPUT
    Motor : BOOL; (* 电机运行命令；TRUE 为运行，FALSE 为停止。 *)
END_VAR

(*
    只有“收到启动请求”且“没有停止请求”时才允许运行。
    将 NOT Stop 与 Start 同时判断，可以保证 Start 和 Stop 同时为 TRUE 时 Motor 为 FALSE，
    从而实现停止优先的安全策略。
*)
Motor := Start AND NOT Stop;
END_FUNCTION_BLOCK

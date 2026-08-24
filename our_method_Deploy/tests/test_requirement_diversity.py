from __future__ import annotations

import pytest

from plc_deploy.requirement_quality import assess_requirement


COMPLETE_REQUIREMENTS = [
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。"
        "Start=TRUE 且 Stop=FALSE 时 Motor=TRUE；Stop=TRUE 时 Motor=FALSE，Stop 优先。"
    ),
    (
        "输入 Start、Stop、Fault、Reset 均为 BOOL；输出 Run、Alarm 均为 BOOL。"
        "上电时 Run=FALSE、Alarm=FALSE。Start 且非 Stop、非 Fault 时 Run 置位并保持；"
        "Stop 或 Fault 清除 Run，Stop 与 Fault 优先于 Start。Fault 置位并保持 Alarm，"
        "仅当 Fault=FALSE 且 Reset=TRUE 时清除 Alarm，Fault 优先于 Reset。"
    ),
    (
        "输入 Enable、SelectA、SelectB 均为 BOOL；输出 PumpA、PumpB 均为 BOOL。"
        "初始 PumpA=FALSE、PumpB=FALSE。Enable=TRUE 且仅 SelectA=TRUE 时 PumpA=TRUE；"
        "Enable=TRUE 且仅 SelectB=TRUE 时 PumpB=TRUE；SelectA 与 SelectB 同时出现时"
        " PumpA=FALSE 且 PumpB=FALSE，冲突停止优先，无保持状态。"
    ),
    (
        "输入 Level 为 REAL、Enable 为 BOOL；输出 Valve 为 BOOL、Deviation 为 REAL。"
        "上电初始 Valve=FALSE、Deviation=0。Enable=TRUE 且 Level<80 时 Valve=TRUE；"
        "Enable=FALSE 或 Level>=80 时 Valve=FALSE；Deviation=100-Level。"
        "Enable 停止优先，输入条件不存在其他冲突。"
    ),
    (
        "输入 Start、Step1Done、Step2Done、Stop、Reset 均为 BOOL；"
        "输出 Step1Run、Step2Run、Complete 均为 BOOL。初始三个输出均为 FALSE。"
        "Start 置位并保持 Step1Run；Step1Done 清除 Step1Run 并置位保持 Step2Run；"
        "Step2Done 清除 Step2Run 并置位保持 Complete；Stop 清除 Step1Run 和 Step2Run；"
        "Reset 清除 Step1Run、Step2Run、Complete。优先级为 Reset、Stop、Step2Done、Step1Done、Start。"
    ),
    (
        "Inputs Start and Stop are BOOL. Output MotorRun is BOOL. Initially MotorRun is FALSE. "
        "When Start is TRUE and Stop is FALSE, MotorRun becomes TRUE. When Stop is TRUE, "
        "MotorRun becomes FALSE. Stop has priority over Start."
    ),
    (
        "inputs: Auto BOOL, Manual BOOL, AutoCmd BOOL, ManualCmd BOOL; "
        "outputs: Valve BOOL, Conflict BOOL. Initially Valve=FALSE and Conflict=FALSE. "
        "If Auto=TRUE and Manual=FALSE and AutoCmd=TRUE then Valve=TRUE. If Manual=TRUE "
        "and Auto=FALSE and ManualCmd=TRUE then Valve=TRUE. If Auto=TRUE and Manual=TRUE "
        "then Valve=FALSE and Conflict=TRUE; the conflict condition has priority."
    ),
    (
        "输入变量\nStart : BOOL\nEmergencyStop : BOOL\n输出变量\nMotor : BOOL\nAlarm : BOOL\n"
        "首次运行 Motor=FALSE、Alarm=FALSE。Start=TRUE 且 EmergencyStop=FALSE 时 Motor=TRUE；"
        "EmergencyStop=TRUE 时 Motor=FALSE 且 Alarm=TRUE。EmergencyStop 优先于 Start，无保持状态。"
    ),
    (
        "输入 HighLevel、LowLevel、EmergencyStop 均为 BOOL；输出 FillValve、DrainValve 均为 BOOL。"
        "上电时 FillValve=FALSE、DrainValve=FALSE。LowLevel=TRUE 且 HighLevel=FALSE 且"
        " EmergencyStop=FALSE 时 FillValve=TRUE；HighLevel=TRUE 且 EmergencyStop=FALSE 时"
        " DrainValve=TRUE；EmergencyStop=TRUE 时 FillValve=FALSE 且 DrainValve=FALSE；"
        "高低液位同时出现时两个输出均为 FALSE，EmergencyStop 优先，无保持状态。"
    ),
    (
        '输入 inputs: [{"name":"Start","type":"BOOL"},{"name":"Stop","type":"BOOL"}]; '
        '输出 outputs: [{"name":"Motor","type":"BOOL"}]. 初始 Motor=FALSE。'
        '当 Start=TRUE 且 Stop=FALSE 时 Motor=TRUE；当 Stop=TRUE 时 Motor=FALSE；Stop 优先于 Start。'
    ),
    (
        "输入 GuardClosed、CycleStart、RobotFault、Reset 均为 BOOL；输出 RobotEnable、FaultLamp 均为 BOOL。"
        "上电初始 RobotEnable=FALSE、FaultLamp=FALSE。GuardClosed=TRUE、CycleStart=TRUE 且"
        " RobotFault=FALSE 时 RobotEnable=TRUE；GuardClosed=FALSE 或 RobotFault=TRUE 时 RobotEnable=FALSE；"
        "RobotFault=TRUE 时 FaultLamp 置位并保持；RobotFault=FALSE 且 Reset=TRUE 时清除 FaultLamp。"
        "RobotFault 与 Reset 同时出现时 RobotFault 优先，GuardClosed=FALSE 优先于 CycleStart。"
    ),
]


@pytest.mark.parametrize("requirement", COMPLETE_REQUIREMENTS)
def test_diverse_user_control_requirements_are_accepted(requirement: str) -> None:
    result = assess_requirement(requirement)
    assert result["ready"] is True, result["missing"]


INCOMPLETE_REQUIREMENTS = [
    (
        "输入 Reset、Pulse 均为 BOOL；输出 Count 为 INT、Done 为 BOOL。初始 Count=0、Done=FALSE。"
        "Pulse 上升沿时 Count 增加 1；Reset=TRUE 时 Count=0 且 Done=FALSE；"
        "Count 达到 10 时 Done=TRUE，Reset 与 Pulse 同时出现时 Reset 优先。",
        {"supported_state_model"},
    ),
    ("帮我写一个水泵控制程序。", {"inputs", "outputs", "behavior", "initial_state", "priority"}),
    (
        "输入变量 BOOL；输出变量 BOOL；当输入时输出变化。初始输出为 FALSE。无输入冲突。",
        {"inputs", "outputs"},
    ),
    (
        "输入 Start；输出 Motor 为 BOOL。当 Start=TRUE 时 Motor=TRUE。初始 Motor=FALSE。Stop 优先。",
        {"inputs"},
    ),
    (
        "输入 Start 为 BOOL；输出 Motor 为 BOOL。系统根据需要自动控制 Motor。初始 Motor=FALSE。Start 优先。",
        {"behavior"},
    ),
    (
        "输入 Start、Fault 均为 BOOL；输出 Motor、Alarm 均为 BOOL。Start=TRUE 时 Motor=TRUE。"
        "初始 Motor=FALSE、Alarm=FALSE。Fault 优先于 Start。",
        {"behavior"},
    ),
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。Start=TRUE 时 Motor=TRUE；"
        "Stop=TRUE 时 Motor=FALSE。采用安全初始状态。Stop 优先于 Start。",
        {"initial_state"},
    ),
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。"
        "Start=TRUE 时 Motor=TRUE，Stop=TRUE 时 Motor=FALSE。输入有优先级。",
        {"priority"},
    ),
    (
        "输入 Start 为 BOOL；输出 Start 为 BOOL。初始 Start=FALSE。Start=TRUE 时 Start=TRUE。无输入冲突。",
        {"interface_consistency"},
    ),
    (
        "输入 Start 为 BOOL；输出 start 为 BOOL。初始 start=FALSE。Start=TRUE 时 start=TRUE。无输入冲突。",
        {"interface_consistency"},
    ),
    (
        "输入 AlarmInput 为 BOOL；输出 Alarm 为 BOOL。初始 Alarm=FALSE。AlarmInput=TRUE 时 Alarm 置位并保持。"
        "不存在输入冲突。",
        {"state_release"},
    ),
    (
        "输入 Start 为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。Start=TRUE 时系统开始运行。Start 优先。",
        {"behavior"},
    ),
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。"
        "Start=TRUE 且 Stop=FALSE 时 Motor=TRUE；Start=TRUE 且 Stop=FALSE 时 Motor=FALSE。"
        "Stop 优先于 Start。",
        {"requirement_consistency"},
    ),
    (
        "输入 Start、Stop 均为 BOOL；输出 Motor 为 BOOL。初始 Motor=FALSE。"
        "Start=TRUE 时 Motor=TRUE，Stop=TRUE 时 Motor=FALSE。"
        "Stop 优先于 Start，同时 Start 优先于 Stop。",
        {"requirement_consistency"},
    ),
]


def test_distinct_comma_separated_conditions_are_not_false_contradictions() -> None:
    requirement = (
        "输入 Fault、Reset 均为 BOOL；输出 Alarm 为 BOOL。初始 Alarm=FALSE。"
        "Fault=TRUE 时 Alarm=TRUE，Fault=FALSE 且 Reset=TRUE 时 Alarm=FALSE。"
        "Fault 优先于 Reset，无保持状态。"
    )
    result = assess_requirement(requirement)
    assert result["ready"] is True, result["missing"]


@pytest.mark.parametrize(("requirement", "expected_missing"), INCOMPLETE_REQUIREMENTS)
def test_ambiguous_or_underspecified_control_requirements_are_rejected(
    requirement: str, expected_missing: set[str]
) -> None:
    result = assess_requirement(requirement)
    observed = {item["id"] for item in result["missing"]}
    assert result["ready"] is False
    assert expected_missing <= observed
    assert all(item["message"] for item in result["missing"])

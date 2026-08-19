# RQ3：台达 DVP48ES300R 厂商工具链迁移证据

本目录保存 RQ3 使用的冻结审计摘要，而不保存候选源代码、API 凭据、Windows 临时工程或冗长运行缓存。数据来自华硕主机上的冻结运行 `dvp48es300r_sonnet5_balanced100_20260818`，于 2026-08-19 拉取。

## 验证协议

候选首先经过 MatIEC、PLCverif 和可见 OpenPLC/ISPSoft--COMMGR 检查；通过可见门后，使用密封 OpenPLC 与 ISPSoft 3.24 + COMMGR 2.11 的 DVP-ES3 模拟器执行终局检查。`dvp48es300r_protocol.json` 是该运行的固定配置。每个最终成功候选均记录了一个通过的密封 DVP 作业。

## 冻结结果

`audit_final.json` 审计了 100 个任务并报告 70 个 `verified_success`。对这 70 个终局成功任务，密封 DVP 作业均为 `pass`；这支持它们在所测试的 DVP48ES300R 厂商编译/仿真配置与选定轨迹上的迁移。其余状态为 10 个 `candidate_budget_exhausted`、6 个 `sealed_failure` 和 14 个 `infrastructure_error`，因此不能将 70/100 表述为无条件的厂商迁移率。

## 文件说明

- `audit_final.json`：任务级冻结审计与 DVP 作业摘要。
- `batch_summary.json`：批处理汇总、候选消耗和终局状态。
- `dvp48es300r_protocol.json`：MatIEC、PLCverif、OpenPLC、ISPSoft/COMMGR 的固定编排配置。
- `generic_vs_dvp_by_category.csv`：RQ1 的通用 IEC Claude Sonnet 5 冻结运行与本 DVP 运行的类别级结果对齐表。
- `audit_reference_differential_final.json`：事后参考实现差分诊断；其 `purpose` 明确为不计入正式评分的假阳性诊断。
- `postbatch_negative_controls.log`：运行后的负对照执行记录；该文件为空，因此不作为独立定量证据。

## 适用边界

本证据覆盖 ISPSoft/COMMGR 的 DVP-ES3 模拟器，不覆盖真实 PLC 下载、现场 I/O、电气时序、厂商专用库或物理设备行为。审计还报告 `adapter_assets_ledgered=false`，因此结果不构成完整的可独立重建厂商适配资产证据；论文中应将结论限定为该冻结环境下的编译与仿真迁移观察。

类别级对齐比较的是两次独立的冻结生成运行：通用 IEC 运行只使用 MatIEC--PLCverif--OpenPLC，而 DVP 运行还将 ISPSoft/COMMGR 的可见反馈纳入循环。它可描述不同类别的端到端结果和失败构成，但不是将同一份候选程序逐个迁移后的因果通过率。

2026-08-19 停止的 24 题、20 候选重试未完成全量执行，故不纳入 RQ3 的冻结结果。

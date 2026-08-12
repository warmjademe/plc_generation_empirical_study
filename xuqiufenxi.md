# PLC 代码生成验证闭环 Harness 需求分析

## 1. 项目目标

开发一套面向 IEC 61131-3 Structured Text（ST）的自动代码生成 Harness。系统调用 Kimi K3 或其他可替换大语言模型，在每个任务最多 10 次完整候选机会内生成 PLC 程序，并严格按照以下顺序验证：

```text
大模型生成完整 ST
        ↓
MatIEC 编译检查
        ↓
PLCverif 形式验证
        ↓
OpenPLC 功能执行
        ↓
成功或进入下一轮
```

任一候选连续通过三个阶段后立即停止。系统的成功含义是“通过预先冻结的三阶段验证协议”，不能表述为程序在所有 PLC 或所有环境中绝对正确。

系统研究的问题是：

> 在固定候选预算下，具有编译、形式反例和功能测试反馈的闭环方法，是否比无反馈的独立采样方法更容易生成满足预先固定需求的 IEC 61131-3 ST 程序？

## 2. 系统边界

### 2.1 系统负责

- 读取公开任务需求和固定接口；
- 调用模型生成完整 ST；
- 保存模型原始响应，不自动修改模型代码；
- 依次调用原始 MatIEC、PLCverif 和 OpenPLC；
- 解析编译错误、形式反例和功能结果；
- 在允许范围内生成下一轮反馈；
- 控制最多 10 个候选并早停；
- 保存请求、代码、日志、反例、轨迹、token、时间和工具版本；
- 支持并发任务、断点恢复和结果审计；
- 实现闭环方法与无反馈独立采样 baseline；
- 在正式模型实验前校准任务、Oracle 和验证基础设施。

### 2.2 系统不负责

- 不重写 MatIEC、PLCverif、nuXmv、CBMC 或 OpenPLC；
- 不使用自制编译器或模拟器替代这些原始工具；
- 不从参考程序运行结果自动生成预期答案；
- 不自动修改或补全模型输出；
- 不根据模型结果修改形式性质、功能 Oracle 或成功标准；
- 不保证程序适用于台达、西门子等具体厂商 PLC；
- 不验证真实硬件时序、电气安全、现场总线或厂商运行时行为；
- 不把有限 OpenPLC 测试通过表述为全部输入和无限轨迹上的证明；
- 不把参考程序、负控程序、形式性质或密封测试答案放入模型上下文。

首期只处理任务明确声明的 IEC 61131-3 ST 子集。超出 MatIEC、PLCverif 或 OpenPLC 共同支持范围的构造应在任务资格检查阶段排除或明确记录。

## 3. 核心术语

- **任务**：由自然语言需求、固定接口、形式性质和功能测试共同定义的 PLC 编程问题。
- **候选机会**：一次成功返回的模型生成响应。无论其中 ST 是否为空、能否提取或能否编译，都消耗一次机会。
- **验证阶段**：MatIEC、PLCverif 或 OpenPLC 中的一个工具调用阶段。
- **形式性质**：由 benchmark 作者预先固定、交给 PLCverif 检查的强制性质。
- **功能 Oracle**：独立设计的输入序列和预期输出，用于 OpenPLC 动态执行检查。
- **参考程序**：人工或独立流程编写的已知合格实现，只用于校准，不用于生成 Oracle。
- **负控程序**：刻意植入明确缺陷、同时保持可编译的程序，用于确认验证器能够拒绝错误实现。
- **可见反馈**：允许发送给模型的编译诊断或形式反例。
- **密封信息**：Harness 内部保存、但不得发送给模型的 OpenPLC 输入、预期输出、实际输出和失败轨迹。
- **基础设施异常**：工具缺失、容器失败、端口冲突或验证器崩溃等不能归因于候选程序的问题。
- **Fail-closed**：只有工具明确满足完整成功条件才算通过；未知、超时和缺失结果均不得作为通过。

## 4. 任务包和模型可见范围

每道任务至少包含：

```text
task_id/
├── metadata.json
├── requirement.md
├── interface.st
├── properties.json
├── openplc_tests.json
├── reference.st
├── negative_control/
│   ├── NC1.st
│   └── index.json
└── validation_report.json
```

模型只能看到：

- `requirement.md`；
- `interface.st`。

模型不得看到：

- `reference.st`；
- `properties.json`；
- OpenPLC 测试输入和预期输出；
- 负控程序；
- 以前的筛选结果。

提示构建器必须使用公开文件白名单，不得递归读取整个任务目录。任务包还应记录 schema 版本、工具支持的 IEC 子集、扫描周期和初始化语义、资源上限以及全部文件哈希。

## 5. 候选机会定义

一次模型成功返回即消耗一个候选机会，包括：

- 空响应；
- 响应格式错误；
- 没有可提取的 ST；
- 编译失败；
- 形式验证失败；
- OpenPLC 功能失败。

以下情况不消耗新候选机会：

- HTTP 429、网络中断等传输异常，且没有收到模型响应；
- 同一候选的工具基础设施重试；
- 中断后重新读取已经保存的模型响应；
- 对同一落盘候选进行幂等恢复。

模型每轮必须输出一个完整 `FUNCTION_BLOCK`，不能只输出补丁。Harness 不得替模型合并补丁或静默修正候选代码。

## 6. 三阶段验证策略

| 阶段 | 回答的问题 | 通过条件 | 前一阶段未通过时 |
|---|---|---|---|
| MatIEC | ST 是否属于支持的 IEC 语法和类型系统 | 退出码为 0、存在预期产物且无结构化编译错误 | 不运行 PLCverif |
| PLCverif | 预先固定的形式性质是否成立 | 所有强制性质均明确为 true | 不运行 OpenPLC |
| OpenPLC | 独立测试序列下的扫描行为是否符合 Oracle | 所有强制用例和检查点均通过 | 候选失败或按密封策略处理 |

### 6.1 MatIEC

MatIEC 回答“代码能否按照支持的 IEC ST 语法和类型规则编译”。它负责检查：

- POU、变量区、声明和数据类型；
- 赋值、表达式和控制结构；
- 未声明变量和不兼容类型；
- 支持的标准函数和功能块调用；
- 程序结构是否完整。

通过条件包括退出码为 0、生成预期产物且没有结构化编译错误。不得通过在输出中搜索单词 `error` 判断失败，因为合法变量名可能包含该字符串。警告是否升级为失败必须在实验前固定。

MatIEC 失败后不得执行 PLCverif 和 OpenPLC。可向模型返回去重、截断后的诊断类别、行列号、主要错误消息和少量相关源码。

### 6.2 PLCverif

PLCverif 必须通过其原始接口调用 nuXmv 或 CBMC 等支持后端，检查任务作者预先冻结的强制性质，不能使用自定义字符串匹配器替代。

要求如下：

- 每条性质具有稳定 ID、对应需求 ID 和 `mandatory` 标记；
- 只有所有强制性质均明确为 true 才能通过；
- 未检查、后端不支持、解析失败、超时和结果缺失均不能算通过；
- 某条强制性质出现首个可信反例后，可以提前停止该候选；
- 如果声称 PLCverif 通过，则必须检查全部强制性质；
- 可信反例必须来自正常完成的后端，并可映射到具体性质和状态轨迹；
- Harness 不得根据模型结果修改性质、环境假设或后端配置。

PLCverif 失败时，可以向模型反馈失败需求 ID、性质描述、一个压缩后的可信反例，以及反例涉及的变量和值。

### 6.3 OpenPLC

OpenPLC 回答“候选在预先设计的输入序列下，扫描行为是否符合独立 Oracle”。OpenPLC 不是自动生成正确答案的工具，其判断依据是：

```text
独立输入序列 + 扫描周期语义 + 预期输出 = 功能测试 Oracle
```

通过条件包括：

- 候选能被 OpenPLC 工具链构建并启动；
- 所有强制测试用例执行完成；
- 所有指定检查点满足预期；
- 没有遗漏检查、运行时崩溃或资源超限。

仅仅成功启动 OpenPLC 不能算功能通过。预期输出必须根据需求独立编写，不能通过运行参考程序自动抄录。

## 7. OpenPLC 一拍执行协议

OpenPLC 后台连续扫描可能造成输入写入和程序扫描错位，因此测试驱动不能只依赖固定时间的 `sleep`。包装程序应实现 request/ack 单拍握手：

1. 测试驱动写入本步骤的全部输入。
2. 驱动切换 `STEP_REQUEST`。
3. 包装程序检测 `STEP_REQUEST <> STEP_ACK`。
4. 包装程序调用 DUT 一次。
5. 将 DUT 输出复制到可观察地址。
6. 执行 `STEP_ACK := STEP_REQUEST`。
7. 驱动等待 ACK 后读取并检查输出。

不同测试用例必须使用全新实例或经过验证的完全重置机制；同一用例内的连续步骤共享内部状态。这样可以测试锁存器、定时器、计数器和状态机，并避免在正式首个输入前执行一次全 FALSE 扫描。

多扫描步骤通过多个 request/ack 循环实现，不能用任意睡眠时间近似扫描次数。候选中的死循环或单拍超时属于候选运行失败；容器无法启动或 OpenPLC 安装损坏属于基础设施异常。

## 8. OpenPLC 反馈边界

推荐的主实验策略是：

- MatIEC 和 PLCverif 是可见反馈层；
- OpenPLC 是密封终局层；
- OpenPLC 输入、预期输出、实际输出、失败步骤和用例名称不得反馈给模型。

如果研究设计要求 OpenPLC 失败后继续生成，最多只能向模型返回：

```text
SEALED_FUNCTIONAL_TEST_FAILED
```

这种设计仍属于对密封 Oracle 的自适应查询，必须在论文中说明，并应另外保留一个从未参与循环的最终确认套件。不得把“终局只调用一次”和“最多十次返回一位失败信息”两种协议的结果混合报告。

## 9. 状态语义与 Fail-closed 规则

每个验证阶段统一返回：

```json
{
  "status": "PASS | FAIL | INCONCLUSIVE | INFRA_ERROR | SKIPPED",
  "reason_code": "稳定机器可读编码",
  "duration_ms": 0,
  "tool_exit_code": 0,
  "tool_version": "...",
  "artifact_hashes": {},
  "details": {}
}
```

- `PASS`：完整满足该阶段预先固定的成功条件；
- `FAIL`：存在可归因于候选程序的可信失败证据；
- `INCONCLUSIVE`：工具运行了，但无法形成可靠判定；
- `INFRA_ERROR`：工具、容器或 Harness 环境异常；
- `SKIPPED`：因前一阶段没有通过而没有执行。

只有三个连续 `PASS` 才能判定成功。`INCONCLUSIVE` 和 `INFRA_ERROR` 不能转换为模型失败或通过；基础设施重试耗尽后，应将任务单独标记为不确定并报告。

## 10. 闭环状态机

```text
TASK_READY
  ↓
BUILD_PROMPT
  ↓
REQUEST_MODEL
  ↓
CANDIDATE_RECEIVED（候选计数 +1）
  ↓
EXTRACT_ST
  ↓
MATIEC
  ├─ FAIL → BUILD_VISIBLE_FEEDBACK
  ├─ 非确定结果 → RETRY_STAGE / INCONCLUSIVE
  └─ PASS
       ↓
    PLCVERIF
       ├─ FAIL → BUILD_VISIBLE_FEEDBACK
       ├─ 非确定结果 → RETRY_STAGE / INCONCLUSIVE
       └─ PASS
            ↓
         OPENPLC
            ├─ FAIL → 按预先冻结的密封策略处理
            ├─ 非确定结果 → RETRY_STAGE / INCONCLUSIVE
            └─ PASS → SUCCESS
```

候选失败后，若候选数小于 10，则构造下一轮提示词；达到 10 次后返回 `FAILED_BUDGET`。任一候选三个阶段全部通过后立即早停，不再生成额外候选选择所谓“更优版本”。

## 11. 闭环方法与 Baseline

Harness 至少实现以下模式：

- `direct`：只生成 1 次，不提供反馈；
- `independent`：最多 10 次，每次只看相同原始任务，候选相互独立；
- `raw_repair`：使用上一候选和有限原始诊断；
- `evidence`：使用需求级证据、可信反例、非回归锚点和确定性修复策略。

所有方法必须使用相同模型、任务、最大候选数、验证工具、OpenPLC Oracle 和费用统计规则。独立 baseline 的提示词不能包含前一候选或任何验证反馈，并应保存每次提示词哈希以审计独立性。

## 12. 反馈和证据管理

反馈压缩必须由确定性代码完成，不应交给另一个 LLM 自由总结。要求包括：

- 编译错误去重；
- 保留首个根因和有限数量的派生错误；
- PLCverif 每轮最多提供一个可信反例；
- 保留原始需求 ID、变量名和状态值；
- 设置反馈字符或 token 上限；
- 保存完整原始证据和实际发送的压缩证据；
- 对 OpenPLC 密封内容进行字段级过滤；
- 记录压缩算法版本及输入、输出哈希。

每次事件写入只追加的 JSONL 证据账本，至少记录：

- 任务和候选编号；
- 模型请求、响应和模型身份；
- 输入、输出和产物哈希；
- 配置及工具版本；
- 验证状态和时间；
- 上一事件哈希与当前事件哈希；
- token、费用和墙钟时间。

账本应能检测事后覆盖，但不能宣称具有硬件级不可篡改性。

## 13. 模型 API 抽象

模型层应定义可替换接口：

```python
class ModelProvider:
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        ...
```

配置只能保存环境变量名称，不得包含明文凭据。例如：

```json
{
  "base_url": "provider endpoint",
  "api_key_env": "KIMI_API_KEY",
  "requested_model": "k3",
  "allowed_resolved_models": ["k3"],
  "max_output_tokens": 8192,
  "timeout_seconds": 600,
  "transport_retries": 6
}
```

每次响应必须记录 API 实际返回的模型名称、响应 ID、finish reason、token 用量和原始响应哈希。如果实际模型不在允许列表中，实验应停止，不能静默回落到其他模型。

模型 API 的传输重试不得修改提示词或采样参数。验证失败不是传输错误，不能对同一模型请求免费重新采样。

## 14. 数据集资格校准

校准不是根据模型结果调整判分标准，而是在正式实验前检查任务和判卷系统是否正常。

### 14.1 参考程序校准

每题的参考程序必须：

```text
MatIEC PASS
PLCverif 全部强制性质 PASS
OpenPLC 全部功能检查 PASS
```

参考程序失败说明任务、Oracle、工具适配或参考实现至少有一项存在问题，该任务不得进入模型实验。

### 14.2 负控校准

每题的负控程序必须：

```text
MatIEC PASS
PLCverif 或 OpenPLC 至少一个明确 FAIL
```

负控必须是已知非等价缺陷，不能仅仅“随便翻转第一个常量”。当前组合任务使用明确的监督故障：

```st
(* 正确 *)
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

(* 负控 *)
CrossBlocked := FALSE;
```

任务同时必须包含对应 PLCverif 不变量，以及 OpenPLC 中 `SubsystemBEnable=TRUE`、`CrossReady=FALSE`、`CrossBlocked=TRUE` 的独立观察点。

该统一负控是验证器最低敏感性的校准哨兵，不是变异测试样本，不能用它声称覆盖了所有子系统错误。修改任务、Oracle、适配器或配置后必须提升版本、更新哈希并重新校准所有受影响任务。

## 15. 并发、恢复和资源隔离

- 不同任务可以并行；
- 同一任务中的反馈候选必须顺序执行；
- 为模型 API、PLCverif 后端和 OpenPLC 分别设置并发上限；
- 每个候选使用独立工作目录、容器、端口和临时文件；
- OpenPLC 用例之间不得共享持久化目录；
- API 429 和 5xx 使用有限指数退避；
- 验证阶段设置进程级 timeout、CPU、内存、磁盘和日志大小限制；
- 每次状态转换立即追加账本并原子写入结果；
- 恢复时根据候选、任务和配置哈希复用已完成阶段；
- 中断恢复不得重新消耗已经收到的模型响应；
- 候选、任务或配置发生变化时，旧缓存必须失效。

## 16. 安全要求

模型生成的 ST 属于不可信输入。所有工具调用必须满足：

- 验证容器禁止访问互联网；
- 使用非特权用户；
- 限制 CPU、内存、进程、磁盘和墙钟时间；
- 不挂载 SSH、API 配置或用户主目录；
- 不向容器暴露 Docker socket；
- 使用参数数组启动进程，避免拼接 shell 命令；
- 校验任务 ID 和文件名，防止目录穿越；
- 限制标准输出和错误输出大小；
- 对 Authorization header、环境变量和异常日志脱敏；
- API key 只能来自环境变量；
- 发布复现包前执行凭据扫描。

## 17. 推荐模块和 CLI

推荐目录：

```text
our_method/
├── configs/
├── prompts/
├── schemas/
├── src/plc_harness/
│   ├── cli.py
│   ├── config.py
│   ├── task_loader.py
│   ├── prompt_builder.py
│   ├── candidate_extractor.py
│   ├── state_machine.py
│   ├── feedback.py
│   ├── ledger.py
│   ├── workspace.py
│   ├── results.py
│   ├── models/
│   └── validators/
├── scripts/
├── tests/
└── runs/
```

建议 CLI：

```bash
plc-harness qualify --dataset DATASET --config CONFIG

plc-harness run \
  --dataset DATASET \
  --config CONFIG \
  --mode evidence \
  --max-candidates 10 \
  --workers 10 \
  --output RUN_DIR

plc-harness run \
  --dataset DATASET \
  --config CONFIG \
  --mode independent \
  --max-candidates 10 \
  --workers 10 \
  --output RUN_DIR

plc-harness validate --task TASK_DIR --candidate PROGRAM.st --config CONFIG
plc-harness resume --run RUN_DIR
plc-harness audit --run RUN_DIR
plc-harness report --run RUN_DIR
```

## 18. 测试计划

### 18.1 单元测试

- ST 代码提取、空响应和多代码块处理；
- 候选计数和早停；
- MatIEC 退出码与诊断解析；
- PLCverif true、false、unsupported、timeout 和结果缺失；
- OpenPLC 预期值类型检查；
- 反馈去重、截断和密封信息过滤；
- baseline 提示词独立性；
- 哈希链验证和断点恢复。

### 18.2 OpenPLC 时序测试

- 一个 request 只执行一次 DUT；
- ACK 与请求严格匹配；
- 连续步骤保持内部状态；
- 不同用例不共享状态；
- 输入不会发生一拍错位；
- 后台扫描不会重复调用 DUT；
- 能区分候选死循环和容器启动失败。

### 18.3 验证器集成测试

- MatIEC 合法和非法语法；
- 编译合法但违反形式性质；
- 全部形式性质通过；
- OpenPLC 构建失败和功能输出错误；
- 计时、计数、边沿和状态机行为；
- 后端不支持、超时和工具崩溃。

### 18.4 任务资格测试

- schema 和 manifest 哈希检查；
- 参考程序三阶段全通过；
- 负控保持可编译且被预期验证阶段拒绝；
- 强制需求具有形式性质或功能测试覆盖；
- Oracle 不依赖参考程序执行生成；
- 私有文件不会进入模型提示词。

### 18.5 端到端测试

- Mock 模型依次返回语法错误、形式错误、功能错误和正确程序；
- 验证反馈顺序和成功后早停；
- 模拟 API 429、PLCverif 超时和 OpenPLC 容器失败；
- 模拟进程中断后恢复；
- 多任务并发时验证目录、端口和状态隔离；
- 在固定环境中重放同一候选并比较验证结果。

## 19. 验收标准

实现必须同时满足：

1. 验证顺序始终为 MatIEC → PLCverif → OpenPLC。
2. 前一阶段未明确通过时不运行后一阶段。
3. PLCverif 失败可在首个可信反例后早停，但通过必须检查全部强制性质。
4. OpenPLC 使用独立 Oracle，不从参考程序输出生成答案。
5. OpenPLC 使用经过测试的 request/ack 一拍语义。
6. 不同 OpenPLC 用例没有状态泄漏。
7. 只有三个阶段全部明确通过才返回成功。
8. 空响应、格式错误和编译失败均消耗候选机会。
9. 单任务最多 10 次模型响应，并在首个成功候选后早停。
10. OpenPLC 密封输入、预期和实际输出不会泄漏进提示词。
11. 独立 baseline 不使用历史候选或验证反馈。
12. 参考程序和负控完成校准后任务才能进入实验。
13. 基础设施异常与模型失败分开统计。
14. 所有候选、提示词、证据、工具版本和 token 可审计。
15. 中断恢复不会重复模型调用。
16. Harness 不修改模型生成的 ST。
17. 配置、代码和日志中不包含明文凭据。
18. 给定固定候选和固定环境，验证结果可以重放。

## 20. 论文评价指标

主要报告：

- `Success@1`；
- 固定预算内真实累计的 `Success@1` 至 `Success@10`；
- 每个任务首次成功所需候选数；
- MatIEC、PLCverif 和 OpenPLC 各阶段失败分布；
- 从一种失败转移到下一阶段或成功的修复比例；
- 首个可信反例对后续候选的修复效率；
- 每个成功任务的 token、API 费用、验证时间和墙钟时间；
- 重复错误率和需求回归率；
- 基础设施异常率；
- 参考程序通过率和负控杀死率。

闭环候选不是独立同分布样本，不应直接使用假定独立采样的 `pass@k` 估计式，应报告真实累计成功曲线。方法比较以任务为配对单位，并报告置信区间、效应量和必要的多重比较校正。

建议至少进行以下消融：

- 只有 MatIEC 反馈；
- MatIEC 与 PLCverif 反馈；
- 只反馈失败性质而不提供反例；
- 完整证据闭环；
- 无反馈独立采样 baseline。

## 21. 效度威胁与结论边界

- 如果最终 50 题来自 Kimi K3 在 200 题中的首次失败，它只能称为 Kimi-K3 条件化 challenge set，不能用于估计 Kimi 在一般 PLC 任务上的总体准确率。
- 筛选阶段的模型调用不能复用为正式 baseline 或方法结果，正式比较必须重新调用。
- 若根据所选 50 题继续调整提示词或 Harness，再在同一批任务上报告结果，会产生方法调优泄漏。
- 有限 OpenPLC 测试不能覆盖所有执行轨迹。
- PLCverif 只能证明已形式化的性质，遗漏需求不会自动被发现。
- MatIEC、PLCverif 转换、验证后端、I/O 映射和测试驱动本身都可能存在缺陷。
- 多次返回 OpenPLC 一位结果仍属于自适应使用密封 Oracle。
- OpenPLC 与真实厂商 PLC 的扫描、定时器和扩展语义可能不同。
- 类别均衡是实验设计选择，不代表工业任务的自然分布。
- API 模型别名可能随时间漂移，因此必须记录调用日期和返回模型身份。

建议同时保存完整 200 题筛选结果，并把筛选出的 50 题定位为 challenge set。闭环方法与 baseline 应在相同任务、模型、验证链和候选预算下使用新的独立调用进行比较。

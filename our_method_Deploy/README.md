# PLC ST and Ladder Generation Service

本目录提供面向台达 PLC 的证据引导程序生成 Web 服务。用户提交控制需求并选择 DVP48ES300R 或 AS228T-A、程序类型和大语言模型；系统先检查需求完整性，再生成验证契约并运行生成—验证—反馈—修正闭环。Structured Text 与梯形图共享同一语义验证流程，梯形图还会输出可视化和厂商原生工件。

当前发布状态为受控内部试运行。对外生产放行条件、已完成证据和剩余阻断项见 `release_tests/PRODUCTION_READINESS_REVIEW_20260824.md`；严格发布门禁未通过时，不得仅依据页面可用或短时 canary 结果宣称生产就绪。

Web 页面采用服务器端登录控制。未登录用户只能访问登录页和健康检查；登录成功后，服务器签发仅供 HTTPS 使用的 HttpOnly、SameSite 会话 Cookie，厂商目录、ST 生成页面及全部任务接口均要求有效会话。`PLC_WEB_API_TOKEN` 仅保留给受控的非浏览器 API 客户端。台达 `DVP48ES300R` 与 `AS228T-A` 任务还会通过持久 RDP 重定向队列发送到独立 Windows worker；worker 串行运行 ISPSoft 3.24、COMMGR 2.11 以及型号对应的 DVP-ES3 或 AS200 Simulator，并将厂商编译与运行 Oracle 结果返回生成循环。

生成期间，页面通过只读进度接口展示当前候选编号、模型调用、MatIEC、PLCverif、两组 OpenPLC 测试以及反馈整理阶段。进度信息从已有运行证据中派生，不改变验证顺序、Oracle 或停止规则，也不向浏览器返回原始反例文件。

## 为什么先确认契约

MatIEC 只能检查 IEC ST 的语法和类型。PLCverif 与 OpenPLC 也只能判断程序是否满足给定性质和测试，无法自动判断这些 Oracle 是否正确表达用户的自然语言意图。因此，本服务先把跨扫描周期的布尔状态写成显式初值、置位条件、清除条件、冲突优先级和保持规则，再确定性模拟所有契约测试，并对同一观测点检查形式性质。系统同时生成需求追踪矩阵：每条冻结需求必须关联至少一个形式性质或状态规则，并同时关联反馈测试和确认测试；安全关键需求必须具有形式性质。对于明确给出的输入优先级，系统还会执行反事实检查，保证低优先级事件在高优先级事件同时有效时不能改变受管理状态。任何语义矛盾或需求覆盖缺口都会在生成 ST 前拒绝，未通过当前审计的契约也不能被人工或倒计时自动确认。审计能够排除可机械判定的内部矛盾和漏测需求，但不能证明契约完全等价于用户意图，因此界面仍允许用户在冻结前核对契约，最终状态表述为“通过已确认契约”，而不是“对真实设备无条件正确”。

## 型号化交付与验证边界

对于 DVP48ES300R 或 AS228T-A，默认交付物是所选型号限定的可下载 ISPSoft 工程。系统先用地址无关的功能块运行全部 Oracle；用户在契约确认页核对型号内置 I/O、有效电平和安全逻辑值后，系统确定性生成独立生产 `MAIN`，Windows worker 再移除测试 harness、导入生产 `MAIN`、重新编译并封装完整 ISPSoft 项目。ST 任务同时保留完整 ST 功能块和 FBU；LD 任务同时保留 Ladder IR、SVG、等价 ST 和原生 `[FB,LD]` FBU。每个成功任务还包含 I/O 映射、点检清单、目标型号、工具链结论以及各工件 SHA-256。也可选择只交付不绑定现场地址的验证功能块。

当前可下载工程模式只覆盖两款 CPU 的内置数字 I/O，并固定使用已校准的 100 ms 周期任务模板。扩展模块、模拟量、运动、网络通信和特殊保持区不会被自动猜测；这些需求必须在接入对应硬件组态配置文件后才能开放。即使项目已经通过 ISPSoft 编译和 COMMGR 功能 Oracle，真实 PLC 下载、逐点 I/O 检查、安全回路验收和现场联调仍是投产前的强制步骤。

- `Structured Text (ST)` 适用于页面列出的全部控制器。`梯形图 (LD)` 当前对台达 `DVP48ES300R` 与 `AS228T-A` 开放：模型生成类型化 Ladder IR，服务确定性输出 SVG 与等价 ST，并把同一 IR 导出为 ISPSoft 原生 `[FB,LD]` 功能块。等价 ST 经过 MatIEC、PLCverif 和 OpenPLC，原生 LD 功能块再经过对应型号的 ISPSoft 编译与 COMMGR Oracle。
- 两个台达型号的原生 LD 导出器当前校准范围为 BOOL 常开/常闭触点、AND/OR 串并联拓扑和普通/置位/复位线圈。复合布尔表达式中的 `NOT` 会先按德摩根律确定性归一化为常闭触点网络。比较、算术、定时器、计数器和边沿块尚未校准；这些构造会失败关闭并作为生成反馈，不能据此声称已支持对应原生梯形图。
- 通用链路为 `MatIEC -> PLCverif -> OpenPLC primary feedback -> OpenPLC confirmation feedback`，两组 OpenPLC 失败均用于后续 ST 修正。
- `DVP48ES300R` 额外执行 `ISPSoft compile -> COMMGR connect -> DVP-ES3 all-case Oracle`；`AS228T-A` 执行对应的 `ISPSoft compile -> COMMGR connect -> AS200 all-case Oracle`。厂商门禁是最终成功条件，确定的编译或运行失败会作为下一候选的修正证据；基础设施未完成不会被计为程序失败。
- 生产目录只提供台达 DVP48ES300R 与 AS228T-A，不接受西门子、东芝或其他未接入官方验证链的厂商型号。
- 默认大语言模型为 DeepSeek V4 Pro；Claude Sonnet 5 使用 `openai-proxy-anthropic` 的 Anthropic 原生协议通道。不可用的 Teamorouter Sonnet 5、DeepSeek V4 Flash 与 Kimi K3 已从生产目录删除。各提供方令牌仅从服务器的独立环境变量读取，页面不提供凭据输入或显示区域。默认最多生成 20 个候选，并在验证成功后立即停止。
- 主页通过最小的真实推理请求显示每个模型通道的在线状态，因而可以识别“网关可访问但具体 Sonnet 通道返回 503”等故障。创建任务前只对所选模型执行最长 12 秒的快速探测；同一模型的并发探测会合并为一次请求，避免多用户同时提交造成探测风暴。仪表板探测结果缓存 5 分钟，手动强制刷新最小间隔为 30 秒；界面不接收或返回服务器令牌。
- 外部接口仅允许 `BOOL`、`INT` 和 `REAL`。这是当前 OpenPLC 驱动器已经校准的范围，不支持的类型会在契约阶段被拒绝，而不是跳过验证。
- 提交前必须通过确定性需求门禁：输入、输出及 IEC 类型、接口名称与类型一致性、每个输出与已声明变量关联的确定控制规则、逐输出初值、冲突优先级，以及保持状态的逐输出退出条件均需给出。门禁还会拒绝未量化时间/阈值、未指定边沿、未声明信号、冲突初值、恒定值与行为冲突、保持与下一扫描清除冲突、多节点优先级环、提示注入、脚本标记、不可见字符、超长和高度重复正文。失败响应返回阻断项、证据与修改建议，并在模型状态探测和任务创建之前终止，因此不会产生模型费用。
- 浏览器使用当前标签页的 `sessionStorage` 保存活动任务 ID；在服务器已接收 POST 但浏览器尚未收到 job ID 的窗口内，还会保存原请求和幂等键。强制刷新后会从服务端持久存储恢复任务，或使用相同幂等键安全重放原请求，不会重复启动模型任务。短时网络中断按照 2、4、8、16、30 秒的有界退避重连，不会取消服务器端任务；用户也可以主动取消，取消标记会中止后续模型调用和验证进程。
- 生产环境使用 PostgreSQL 保存任务和幂等键，Web 进程只负责请求；独立生成 worker 通过可续租任务租约取得执行权。进程退出后，其他 worker 只在租约过期后从不可追加修改的候选账本续跑，已支付且已完成的候选不会被重复生成。SQLite 仅保留为单进程本地开发后端。
- 每个模型通道具有独立的并发上限、每分钟请求上限、排队超时和连续瞬态失败熔断器。生产只运行一个生成 worker 服务，因此所有任务共享同一套提供方配额；增加 Web 进程不会放大模型调用并发。
- 厂商验证使用 worker 池。每台 Windows 虚拟机拥有独立私网、RDP 桥、spool、worker 身份和串行 ISPSoft/COMMGR 桌面；Linux 按目标能力和排队长度分配任务，回执身份不匹配时失败关闭。节点进入 draining 或 quarantined 状态后不再接收任务。

## 本地开发

```bash
conda create -n plc_generation python=3.11 -y
conda run -n plc_generation pip install -e '.[test]'
conda run -n plc_generation pytest -q
PLC_WEB_API_TOKEN=change-me PLC_LOGIN_USERNAME=kemei PLC_LOGIN_PASSWORD=change-me PLC_SESSION_SECRET=change-me-too conda run -n plc_generation plc-generation-web
```

服务默认只监听 `127.0.0.1:18081`，由独立的 Caddy 实例在外部 `18080` 端口提供 HTTPS 反向代理。独立实例不使用主机上其他业务动态管理的 Caddy 配置。生产环境的模型密钥和访问令牌放在仓库之外的私有环境文件中，权限为 `600`；仓库和任务日志中不得出现明文凭据。

## 生产目录

```text
/opt/plc-generation/app      # 本目录代码
/opt/plc-generation/tools    # MatIEC/PLCverif/nuXmv/CBMC
/opt/plc-generation/data     # PostgreSQL 数据、任务契约、候选和验证证据
/opt/plc-generation/config/service.env   # 服务参数与 Web 访问令牌，权限 600
/opt/plc-generation/config/providers.env # 模型 API 凭据，权限 600
/opt/plc-generation/config/dvp-validator.env # ISPSoft 源单元封装私密参数，权限 600
/opt/plc-generation/config/dvp-bridge.env    # Windows RDP 私密参数，权限 600
/opt/plc-generation/dvp-bridge-*             # 每台 Windows worker 的独立队列、状态和结果证据
```

`service.env` 中必须设置 `PLC_PROJECT_ROOT=/opt/plc-generation/app`，使已安装的 Python 包仍从部署目录读取提示词、验证脚本、前端静态文件和目录配置。两个环境文件均位于仓库之外，且不得复制到任务工件或运行日志。
PLCverif 基于 Eclipse 运行时，会在 `$HOME/.eclipse` 写入配置缓存；生产服务将 `HOME` 指向 `/opt/plc-generation/data/runtime-home`，避免写入部署账户的真实主目录，并使 systemd 文件系统隔离与命令行预检保持一致。

部署后先运行：

```bash
/home/ubuntu/miniforge3/envs/plc_generation/bin/python scripts/preflight.py
```

厂商 canary、并发池和长稳脚本必须使用生产服务账户（当前为 `ubuntu`）运行。脚本会在改写节点健康状态前核对共享 spool 的所有者；若从 `root` 或其他账户误启动，将以配置错误退出且不会隔离健康的 Windows 节点。

预检要求已知正确程序通过四个门禁，并要求已知错误程序被 PLCverif、可见 OpenPLC 和密封 OpenPLC 拒绝。只有正反样例同时满足才应启动 Web 服务。
关键验证器与 OpenPLC 镜像的固定摘要记录在 `deploy/tool-manifest.json`，部署时应同时比较文件哈希与镜像 ID。

Codex 开源 harness 的持久事件、结构化工具反馈、受限上下文和任务生命周期机制及其在本服务中的对应关系记录于 `CODEX_HARNESS_ADAPTATION.md`。

## API 流程

1. `POST /api/login`：校验用户名和密码并建立浏览器会话。
2. `GET /api/catalog`：登录后读取厂商、控制器型号、模型和默认选项；该接口不触发模型调用。
3. `POST /api/requirements/check`：不调用模型，检查控制需求是否具备生成可靠 Oracle 所需的信息。
4. `POST /api/jobs`：再次执行需求、型号、在线模型、厂商 worker 和并发容量门禁，通过后才创建任务。
5. `GET /api/jobs/{id}`：轮询，状态到达 `awaiting_contract_approval` 时核对契约。
6. `POST /api/jobs/{job_id}/approve`：确认并冻结契约，启动生成与验证闭环。
7. `POST /api/jobs/{job_id}/cancel`：持久记录取消请求；未开始任务立即取消，运行中任务在当前不可中断网络请求返回后停止。
8. 再次轮询任务：`verified_success` 返回通过契约和目标厂商链的程序；`generation_failed` 返回最后候选和错误；`infrastructure_error` 表示验证器、网络或模型服务未能给出确定结论。

任务中心通过 `GET /api/history` 提供服务端分页历史，并支持日期、状态、控制器、程序类型、模型和关键词组合筛选。终局任务可以归档、恢复或删除；默认 180 天后自动进入归档视图，删除操作同时把运行工件移动到服务器受限的回收目录。

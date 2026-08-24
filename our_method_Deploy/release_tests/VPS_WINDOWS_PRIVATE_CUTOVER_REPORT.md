# vps_windows 私网切换与发布验收记录

日期：2026-08-23

## 切换结果

- 科美 VPS 通过专用 TAP 网络直接访问 Windows 11 虚拟机的私网 RDP 服务。
- Windows 虚拟机使用固定内网地址 `10.0.2.15:3389`；生产桥接脚本拒绝回退到公网 RDP 转发。
- 原公网 `43389` 转发已经关闭，避免 ISPSoft/COMMGR 验证流量暴露在公网。
- 虚拟机、私网和验证桥接均由 systemd 托管并设置自动恢复。
- Windows 已关闭交流与直流待机；QEMU 同时从硬件层禁用 S3/S4，以防虚拟机休眠或休止。

## 厂商环境迁移

- DVP48ES300R：ISPSoft 3.24、COMMGR DVP-ES3 仿真器和干净工程模板已就绪。
- AS228T-A：从已校准的旧验证主机导出干净 AS200 工程，在新虚拟机导入后核对 SHA-256，并纳入启动自检。
- 就绪接口按控制器分别检查模板、ISPSoft、对应 COMMGR 仿真器和 worker 心跳；缺失任一前置条件时任务在模型调用前失败关闭。

## 判定尺校准

| 控制器 | 正确参考程序 | 主动构造错误程序 |
|---|---:|---:|
| DVP48ES300R | 通过 | 拒绝 |
| AS228T-A | 通过 | 拒绝 |

Linux 前置工具链还使用同一组正反例完成 MatIEC、PLCverif 和 OpenPLC 校准：正确程序通过全部门，错误程序被语义验证门拒绝。

## 自动化测试

- Python 测试：163 项通过，1 项因生产 VPS 未安装 Node.js 而由测试框架跳过。
- 同一浏览器恢复测试随后在具备 Node.js 的隔离环境中单独执行并通过。
- 合计 164 项逻辑测试通过，覆盖配置、鉴权、契约、任务状态、ST/LD、两种控制器、验证桥接、状态 API 和页面展示。

## 真实模型回归

发布回归采用 2 个模型、2 种控制器和 2 种输出类型，共 8 个组合。每个任务允许最多 20 个候选；最终成功必须通过 MatIEC、PLCverif、OpenPLC 可见与确认测试，以及对应控制器的 ISPSoft/COMMGR 判定。

| 模型 | 控制器 | 输出 | 结果 | 候选数 | 厂商验证 |
|---|---|---|---:|---:|---:|
| DeepSeek V4 Pro | DVP48ES300R | ST | 通过 | 2 | 通过 |
| DeepSeek V4 Pro | DVP48ES300R | LD | 通过 | 1 | 通过 |
| DeepSeek V4 Pro | AS228T-A | ST | 通过 | 1 | 通过 |
| DeepSeek V4 Pro | AS228T-A | LD | 通过 | 7 | 通过 |
| Claude Sonnet 5 | DVP48ES300R | ST | 通过 | 1 | 通过 |
| Claude Sonnet 5 | DVP48ES300R | LD | 通过 | 1 | 通过 |
| Claude Sonnet 5 | AS228T-A | ST | 通过 | 11 | 通过 |
| Claude Sonnet 5 | AS228T-A | LD | 通过 | 1 | 通过 |

8 个组合全部验证成功。DeepSeek V4 Pro 的 4 个组合耗时约 18.8 分钟，Claude Sonnet 5 的 4 个组合耗时约 26.1 分钟；两组并行提交，ISPSoft/COMMGR 厂商验证由单个 Windows worker 串行执行。

## 已知边界

- ISPSoft/COMMGR 是 Windows GUI 工具，单个 worker 串行执行厂商仿真；并行模型生成不会改变这一限制。
- `powercfg /hibernate off` 在非提权 RDP 会话中不可修改，但 QEMU 已从虚拟硬件层禁用 S4，且 Windows 待机超时已设为 0。
- 浏览器恢复测试需要 Node.js；生产主机未为运行服务额外安装该开发依赖，验收在隔离环境完成。

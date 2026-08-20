# Hand of Agents 开发约定

## 架构边界

- `src/hand_of_agents/server/`：Host 上的 FastAPI、节点连接与审计存储。
- `src/hand_of_agents/client/`：树莓派 WebSocket Client、GPIO 与安全状态逻辑。
- `src/hand_of_agents/web/`：独立 HTML/CSS/JS 前端，不把 GPIO 控制逻辑放进页面。
- GPIO 编号统一使用 BCM；40-pin profile 的引脚默认 `unconfigured`，只能通过 `configure` 命令动态申请。
- 动态输出及静态输出都必须遵守 `safe_state`。断线、退出、配置失败和异常路径不得绕过安全状态或遗留已申请设备。
- 物理 27/28 脚是 HAT ID 保留脚，不加入通用 GPIO profile。

## 验证

- 本机开发使用 `gpio_backend = "mock"`，不得要求普通开发机具有 GPIO。
- 提交前运行 `python -m pytest`；协议或 API 变化需同步测试和 `README.md`。
- 实机实验保留原始日志到 `logs/`，记录运行时间、节点、配置和结果；不要提交令牌、密码或 `.env`。

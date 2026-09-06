# Agent 项目规范

## 会话

开始工作时在 `log/` 创建 `YYYY-MM-DD-HH.md`，记录目标、关键决策、进度和风险；完成主要阶段时更新。

## 分工与安全

- 用户决定社群边界、角色、治理、隐私与最终发布；Agent 负责澄清、实现和验证。
- 默认使用虚构数据。未经明确授权，不导入、上传、公开或迁移真实数据。
- `.env`、`data/`、`log/`、成员信息、邀请码和生产快照永不进入 Git。
- AI 只生成指南候选稿，不自动发布，不覆盖较新的人工修改。

## 命名与架构

- 目录、文件、函数和变量使用小写英文 snake_case；Skill 目录按 Skill 规范使用短横线。
- 依赖保持 `app → glue → services → libs → third_party` 单向。
- `app` 只处理 HTTP 与渲染；跨服务编排放 `glue`；业务规则放 `services`；第三方 SDK 由 `libs` 封装。
- service 不调用 service，构造函数只接收 settings；项目内使用绝对导入。
- 文件 I/O 使用 UTF-8 与 `newline="\n"`；路径来自 settings，凭据来自 `.env`。
- 所有 Web 写操作经过 `require_writer` 或 `require_admin`。

## 变更与验证

- 先读 `docs/product_brief.md`、`docs/privacy_inventory.md` 和 `config/community.json`。
- 保留用户已有改动；不使用破坏性 Git 命令。
- 模块变更同时覆盖模型、服务、路由、模板、权限、测试、配置和导出。
- 完成前运行测试、项目验证和公开审计，报告残余风险。

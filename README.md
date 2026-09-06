# Knowledge Common Kit

把一个专业、读书会、学生组织或地方社群的知识积累，变成可以长期共同维护的网站。

这个仓库不是“一键生成网页”的演示，而是一套给普通用户和 AI Agent 协作使用的实践包：你负责社群判断、边界与价值取舍，Agent 负责访谈、配置、编码、测试和部署。它来自一个真实学生社群网站的完整开发与治理实践，但公开版本不包含原社群的成员信息、内容数据、凭据、部署地址或 Git 历史。

English summary: an agent-guided, privacy-first starter kit for building a governed community knowledge hub.

## 你可以搭出什么

模板包含八类可组合能力：动态首页、演化式指南、长文章、活动、讨论广场、统一贡献入口、点赞留言和审核后台。三类账号分别是管理员、成员与只读观察员。

你不必一次启用全部模块。一个读书会可以只用“指南 + 文章 + 贡献”，一个院系社群可以再启用“活动 + 广场”，一个公开资料站也可以保留只读内容并关闭成员互动。

## 最短路径

1. 在 Codex 中直接说：`使用 $skill-installer，从 https://github.com/PeberWang/knowledge-common-kit/tree/main/skills/build-community-hub 安装这个 Skill。`
2. 安装后新开一个任务，对 Agent 说：`使用 $build-community-hub，先采访我，不要急着写代码。帮我搭建一个服务于____的社区网站。`
3. Agent 会先产出需求简报和风险清单，经你确认后再复制并定制模板。

如果你的 Agent 不支持自动安装，就下载整个仓库，并把 `skills/build-community-hub` 整个目录交给它。不要只复制 `SKILL.md`，因为脚本、参考资料和 starter 都属于资源包。

如果你想先自己了解流程，请读 [5 分钟开始](docs/quick_start.md)；如果你不知道该怎么描述需求，请读 [怎样和 Agent 聊](docs/conversation_guide.md)。

## 人与 Agent 怎么分工

| 事项 | 你决定 | Agent 执行 |
|---|---|---|
| 社群边界、目标和禁区 | 是 | 整理并追问 |
| 谁能看、谁能发、谁审核 | 是 | 转成权限和流程 |
| 模块取舍与上线节奏 | 共同 | 给出最小方案并实现 |
| 凭据、真实成员数据、最终发布 | 亲自授权 | 检查，不擅自公开 |
| 编码、测试、文档与部署命令 | 验收 | 负责 |

## 仓库地图

- `skills/build-community-hub/`：可导入的 Skill；其中 `assets/starter/` 是可运行网站模板。
- `docs/`：写给普通发起人与维护者的指南。
- `examples/`：不同类型社群的需求简报示例。
- `SECURITY.md`：隐私、漏洞与公开发布边界。

## 设计原则

- 人工意志优先：AI 只生成候选稿，不能自动覆盖正式知识。
- 数据与代码分离：代码可公开，成员、邀请码、反馈和正文数据默认不进 Git。
- 渐进式建设：先解决一个真实协作问题，再按证据增加模块。
- 贡献有上下文：不只收文件，还收“为什么有用、怎样使用”。
- 事前与事后治理分流：正式内容先审后发，日常讨论先发后管。
- 可退出：不绑定某个 Agent、模型或云厂商，本地模式即可运行。

## 文档入口

- [模块目录与组合建议](docs/module_catalog.md)
- [社群建设手册](docs/community_playbook.md)
- [隐私与公开发布](docs/security_and_privacy.md)
- [部署选择](docs/deployment.md)
- [维护与升级](docs/maintainer_guide.md)

## 技术底座

模板采用 Python 3.10+、FastAPI、Jinja2 与 JSON/Markdown 文件存储。默认本地文件后端无需云账号；需要时可接 OpenAI-compatible LLM、OCR 和对象存储。架构保持 `app → glue → services → libs` 单向依赖，便于 Agent 分层修改。

## 许可证与贡献

代码与文档按 [MIT License](LICENSE) 发布。参与前请阅读 [贡献指南](CONTRIBUTING.md)；安全问题请不要公开提交，按 [SECURITY.md](SECURITY.md) 处理。

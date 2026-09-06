# 你的社区知识站

这是由 Community Site Kit 生成的可运行项目。公开身份与模块开关在 `config/community.json`，私密环境配置在 `.env`，运行数据在 `data/`。

## 本地运行

```bash
bash setup.sh
venv/bin/python scripts/create_admin.py
venv/bin/python run.py
```

打开 `http://127.0.0.1:8790`。先使用虚构账号和内容验收，再考虑导入真实数据或部署。

## 修改顺序

1. 在 `config/community.json` 修改名称、介绍、模块、栏目文案和颜色。
2. 与社群确认 `docs/product_brief.md` 和 `docs/privacy_inventory.md`。
3. 根据真实需求修改模板与规则，并补测试。
4. 运行测试、项目验证和公开审计。

```bash
venv/bin/python -m pytest -q
python /path/to/build-community-hub/scripts/validate_project.py .
python /path/to/build-community-hub/scripts/audit_public.py .
```

AI 生成的指南只能成为候选稿，必须由管理员查看差异后发布。生产数据不可由代码同步覆盖。

# 贡献指南

欢迎修正文档、增加通用模块、改善无障碍与安全性，或提交新的社群实践案例。

提交前请确认：

1. 不包含真实成员数据、密钥、内部链接或未经授权的社群材料。
2. 新能力对多种社群有复用价值，特定组织逻辑通过配置或示例表达。
3. 代码保持 `app → glue → services → libs` 单向依赖，业务规则不写进路由。
4. 新增文件名、目录名和标识符使用小写英文；Skill 名使用短横线。
5. 在 starter 目录运行测试与公开审计。

```bash
cd skills/build-community-hub/assets/starter
python -m pytest -q
python ../../scripts/audit_public.py .
```

请在 Pull Request 中写清目标用户、被解决的问题、取舍和验证方式。

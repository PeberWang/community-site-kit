# 5 分钟开始

## 你只需要准备三样东西

- 一句话：这个社群是谁，眼下最想解决什么问题。
- 一个人：谁愿意做第一任管理员并承担最终判断。
- 一个边界：哪些信息绝不能公开或交给外部模型。

不要先整理几十页需求。把 Skill 导入 Agent 后，直接说：

> 使用 $build-community-hub。请一次只问我一个容易回答的问题，先帮我澄清最小可上线版本。我不熟悉编程，技术选择请给出默认建议和影响。

Agent 应先与你完成访谈，生成 `docs/product_brief.md`、`docs/privacy_inventory.md` 和 `config/community.json` 草案。只有你确认后，它才开始搭建。

## 导入 Skill

把 `skills/build-community-hub` 整个目录放进你的 Agent 的 Skills 目录，或让 Agent 直接读取这个目录。不要只复制 `SKILL.md`，因为脚本、参考资料和 starter 都是资源包的一部分。

## 生成第一个项目

Agent 通常会运行：

```bash
python skills/build-community-hub/scripts/bootstrap_project.py \
  --destination ./my_community_site \
  --name "我的社群知识站" \
  --community "我的社群"
```

随后在新目录中：

```bash
bash setup.sh
venv/bin/python scripts/create_admin.py
venv/bin/python run.py
```

浏览器访问 `http://127.0.0.1:8790`。本地体验不需要购买服务器、域名、对象存储或模型 API。

## 第一次验收只看五件事

1. 新成员是否能在一分钟内明白网站的用途。
2. 只读者、成员和管理员的权限是否符合约定。
3. 一次贡献是否能说清“它是什么、为什么有用、属于哪里”。
4. 管理员是否能审核、纠错和保留版本。
5. 关掉电脑前，数据是否知道存在哪里、怎样备份。

通过后再讨论部署。不要把真实成员数据拿来做第一次测试。

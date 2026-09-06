# 安全与隐私

请不要在公开 Issue 中提交密钥、真实邀请码、成员名单、私人联系方式、未公开内容或可定位服务器的信息。发现漏洞时，请通过 GitHub Security Advisory 私下报告，并只提供复现所需的最少数据。

公共模板中的 `.env.example` 只能放占位符。真实配置放在 `.env`，运行时数据放在 `data/`；两者均被 Git 忽略。发布前必须运行：

```bash
python skills/build-community-hub/scripts/audit_public.py <项目目录>
```

检查通过并不代替人工判断。姓名、组织内部文档、历史讨论、图片元数据、域名、IP 和对象存储路径都可能泄露身份或组织关系。

生产环境至少应使用 HTTPS、32 位以上随机会话密钥、Secure Cookie、私有对象存储、最小权限凭据和定期备份。公开模板不应包含任何生产数据快照。

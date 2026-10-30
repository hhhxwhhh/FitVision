# 安全策略

## 支持版本

安全修复会合并到 `main` 分支。请始终基于最新 `main` 部署。

## 报告安全问题

**请不要通过公开 Issue 报告安全漏洞。**

优先使用 GitHub 的私密漏洞报告：

1. 打开仓库的 **Security → Advisories → Report a vulnerability**。
2. 描述漏洞影响、复现步骤与建议修复方式。
3. 我们会尽快确认并回复。

## 密钥与配置

- 所有密钥只能放在 `.env` 中；`.env` 已被 `.gitignore` 排除。
- 仓库仅提交 `.env.example` / `.env.docker.example` 模板。
- 如果怀疑密钥曾进入版本库：**立即在对应平台撤销并重新生成**。从 Git 历史中删除文件并不能使已泄露的密钥重新安全。
- 生产环境必须设置强随机 `SECRET_KEY`，并保持 `DEBUG=False`。
- 建议为数据库、Redis、LLM API 使用独立账号与最小权限。

## 部署检查清单

- [ ] `DEBUG=False`，`SECRET_KEY` 来自密钥管理系统
- [ ] `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` 配置为实际域名
- [ ] 全站 HTTPS，反向代理传递 `X-Forwarded-Proto`
- [ ] 定期轮换 JWT、数据库与第三方 API 密钥
- [ ] 备份数据库与用户上传的媒体文件
- [ ] 关注 Dependabot 的安全更新提示

## 改动说明

<!-- 这个 PR 解决什么问题？用户能感知到什么变化？ -->

## 改动类型

- [ ] feat：新功能
- [ ] fix：缺陷修复
- [ ] refactor：重构（不改变行为）
- [ ] perf：性能优化
- [ ] docs：文档
- [ ] chore / ci：工程化

## 验证方式

<!-- 列出你执行的命令或手动验证步骤，便于 Review -->

```bash
# 前端
cd frontend && npm run lint && npm run type-check && npm run build

# 后端
cd backend
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py check
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py test
```

## 截图 / 录屏

<!-- 界面改动请附前后对比；纯后端改动可删除本节 -->

## 检查清单

- [ ] 已补充或更新测试
- [ ] 已更新相关文档
- [ ] 未提交 `.env`、密钥、模型缓存或构建产物
- [ ] 破坏性变更（API / 数据库 / 配置）已在说明中标注

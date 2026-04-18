# dev_y 分支被处理掉的后端差异说明

## 1. 背景与基线

- 合并提交: 403ae7af429a3e3291ce2fae3c4d2098bc4199a6
- main 父提交: 2d3b8f7579de4f567674f23db5e0ffc0e146d078
- dev_y 父提交: 59eaf343c7ad577ebc4317144277ea4e3adafec9
- 冲突策略: 后端冲突优先保留 main（ours）

本文件中的“被处理掉差异”含义为：在 dev_y 中存在、但最终没有进入 main 的后端改动。

## 2. 对比范围与方法

对比范围限定为本次冲突核心后端文件：

- backend/recommendations/services.py
- backend/training/services.py
- backend/training/views.py

对比方法：

- 使用 403ae7a -> 59eaf34 的反向差异查看 dev_y 独有改动。
- 结合冲突处理策略（ours）确认这些改动未进入最终 main。

## 3. 规模统计

- backend/recommendations/services.py: 991 行变化
- backend/training/services.py: 232 行变化
- backend/training/views.py: 543 行变化
- 合计: 3 个文件，1082 行新增、684 行删除（以 dev_y 视角）

## 4. 逐文件详细差异

### 4.1 backend/recommendations/services.py

#### A. dev_y 新增但未进入 main 的核心能力

1) 引入场景化混排与权重融合框架（HybridRecommender 大幅重构）
- 新增 DEFAULT_ALGORITHMS、SCENARIO_ENGINE_WEIGHTS。
- 新增多路召回融合方法：_blend_sources。
- 新增多样性重排：_rerank_with_diversity。
- 新增探索率自适应：_compute_exploration_ratio、_select_with_exploration。

2) 引入目标导向重排
- 新增用户目标解析：_resolve_user_goal（优先 UserGoal，再回退体重差推断）。
- 新增目标匹配加分：_goal_fit_bonus。
- 新增目标重排：_rerank_by_user_goal。

3) 引入疲劳与目标联动惩罚
- 新增强度估计：_strength_intensity。
- 新增疲劳抑制重排：_rerank_by_goal_and_fatigue。
- 逻辑重点：在增肌目标且疲劳高时，下调高强度动作分数。

4) 引入近期重复曝光屏蔽
- 新增 _recent_blocked_ids，屏蔽最近行为与已看过推荐。

5) 推荐缓存与清理逻辑增强
- default 场景使用 DEFAULT_ALGORITHMS 过滤。
- 非 default 场景使用 scenario:algorithm 前缀过滤与清理。

#### B. dev_y 里的性能与稳定性微改动（也未进入 main）

1) 内容推荐与序列推荐中，增加 in_bulk 批量取数减少查询次数。
2) GNN 权重加载失败时改为 logger 记录，并在缺权重时提前返回空结果。
3) 若干异常处理与日志方式调整（print -> logger）。

#### C. dev_y 对 main 现有保护逻辑的变更（未生效）

1) 解锁过滤（前置动作达标校验）在 dev_y 版本被移除。
- main 中对推荐结果与兜底结果存在 UserExerciseRecord 达标校验。
- 由于最终保留 main，此移除未生效。

结论：recommendations 服务层中，dev_y 的大部分“新推荐策略与重排能力”本次未进入 main。

---

### 4.2 backend/training/services.py

#### A. dev_y 新增但未进入 main 的改动

1) 新增目标解析兜底方法 _resolve_goal
- 优先读取 profile.goal。
- 若无则回退读取用户 active goal（muscle_gain/weight_loss 映射）。

2) 冷启动相似用户逻辑字段兼容调整
- dev_y 使用 target_user.profile 路径。
- 并在无 profile 时提前返回。

#### B. dev_y 删除但未生效（main 仍保留）的能力

1) 手动选动作解锁校验
- verify_manual_selection 在 dev_y 中被删。
- main 仍保留该能力。

2) 训练前 AI 难度评估
- evaluate_plan_difficulty 在 dev_y 中被删。
- main 仍保留该能力。

3) 相关依赖清理未生效
- dev_y 中配套移除了 os、requests、UserExerciseRecord 等依赖。
- 由于 main 保留相关功能，这些依赖也继续保留。

结论：training 服务层中，dev_y 方向主要是“删减训练前校验链路 + 目标字段兼容”，本次未进入 main。

---

### 4.3 backend/training/views.py

#### A. dev_y 对训练启动流程的改动（未进入 main）

1) start_training_session 简化
- 移除 exercise_ids 动态散装动作分支。
- 移除 records_to_create + bulk_create 逻辑。
- total_exercises 在无 plan_day 时由 len(exercise_ids) 改为 0。

影响：若按 dev_y 行为，前端传自定义动作列表时的训练记录初始化会弱化。

#### B. dev_y 对图谱更新的并发改法（未进入 main）

1) complete_training_session 中边权更新方式
- dev_y 使用 F 表达式原子更新：update(weight=F("weight") + weight_add)。
- main 保持对象加权后 save 的写法。

影响：dev_y 版本对高并发写权重更安全；本次未合入。

#### C. dev_y 删除但未生效（main 仍保留）的接口

1) pre_workout_analysis 在 dev_y 中被移除。
- main 仍保留该接口（包含动作解锁硬校验 + AI 软校验建议）。

结论：training 视图层中，dev_y 的主方向是“简化训练启动与移除训练前拦截接口”，本次未进入 main。

## 5. 汇总结论

本次由于后端冲突按 main 优先，dev_y 的后端差异主要被处理掉在三类能力上：

1) 推荐系统升级链路
- 目标导向重排
- 疲劳联动抑制
- 多样性重排
- 探索率自适应

2) 训练前置链路取舍
- dev_y 倾向删减训练前解锁与 AI 评估
- main 保留闭环拦截

3) 工程性优化未落地
- 部分批量查询优化
- 部分并发安全更新写法
- 部分日志体系调整

## 6. 后续回补建议（可选）

建议拆成独立后端修复分支分批回补，避免一次性引入回归：

1) 第一批（低风险）
- 仅回补性能与并发优化：in_bulk、F 原子更新、日志替换。

2) 第二批（中风险）
- 回补目标导向重排与疲劳联动，但保留 main 的解锁校验。

3) 第三批（高风险）
- 再评估是否引入探索率和多样性策略，配套补测试与线上观测指标。

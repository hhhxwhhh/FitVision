<template>
    <div class="page-container">
        <div class="page-header-row">
            <h1 class="page-title">动作百科</h1>
            <div class="header-actions">
                <el-select v-model="ordering" placeholder="排序方式" size="large" class="sort-select" @change="fetchExercises">
                    <el-option label="默认排序" value="order" />
                    <el-option label="难度从低到高" value="level" />
                    <el-option label="难度从高到低" value="-level" />
                    <el-option label="名称 (A-Z)" value="name" />
                </el-select>
                <el-input v-model="search" placeholder="搜索动作名称..." size="large" class="search-input" clearable @clear="handleSearchClear">
                    <template #prefix>
                        <el-icon class="search-icon"><Search /></el-icon>
                    </template>
                </el-input>
            </div>
        </div>

        <el-card class="filter-card mb-4" :body-style="{ padding: '16px 20px' }">
            <div class="filter-container">
                <div class="filter-row">
                    <span class="filter-label">部位筛选:</span>
                    <el-radio-group v-model="filter.target_muscle" size="default" class="custom-radio-group">
                        <el-radio-button label="">全部</el-radio-button>
                        <el-radio-button label="chest">胸部</el-radio-button>
                        <el-radio-button label="back">背部</el-radio-button>
                        <el-radio-button label="shoulders">肩部</el-radio-button>
                        <el-radio-button label="arms">手臂</el-radio-button>
                        <el-radio-button label="abs">腹部</el-radio-button>
                        <el-radio-button label="legs">腿部</el-radio-button>
                    </el-radio-group>
                </div>
                
                <div class="filter-row mt-2">
                    <span class="filter-label">难度等级:</span>
                    <el-radio-group v-model="filter.difficulty" size="default" class="custom-radio-group">
                        <el-radio-button label="">全部</el-radio-button>
                        <el-radio-button label="beginner">入门</el-radio-button>
                        <el-radio-button label="intermediate">中级</el-radio-button>
                        <el-radio-button label="advanced">高级</el-radio-button>
                    </el-radio-group>
                </div>

                <div class="filter-row mt-2">
                    <span class="filter-label">器械要求:</span>
                    <el-radio-group v-model="filter.equipment" size="default" class="custom-radio-group">
                        <el-radio-button label="">全部</el-radio-button>
                        <el-radio-button label="none">无器械</el-radio-button>
                        <el-radio-button label="dumbbell">哑铃</el-radio-button>
                        <el-radio-button label="barbell">杠铃</el-radio-button>
                        <el-radio-button label="machine">器械</el-radio-button>
                    </el-radio-group>
                </div>
            </div>
        </el-card>

        <el-row :gutter="24" v-loading="loading">
            <el-col v-for="ex in exercises" :key="ex.id" :xs="24" :sm="12" :md="8" :lg="6">
                <el-card class="exercise-card hover-lift" :body-style="{ padding: 0 }">
                    <div class="card-image-wrapper">
                         <img :src="ex.image_url || 'https://via.placeholder.com/300x200?text=FitVision'"
                            class="image" loading="lazy" />
                         <div class="difficulty-badge" :class="ex.difficulty">
                             {{ ex.difficulty_display }}
                         </div>
                    </div>
                    
                    <div class="card-content">
                        <div class="title-row">
                            <h3 class="title" :title="ex.name">{{ ex.name }}</h3>
                        </div>
                        
                        <div class="tags-row">
                            <el-tag size="small" type="info" effect="plain" round>🎯 {{ ex.target_muscle_display }}</el-tag>
                            <el-tag size="small" type="info" effect="plain" round v-for="tag in ex.tags" :key="tag"># {{ tag }}</el-tag>
                        </div>
                        
                        <p class="desc">{{ ex.description }}</p>
                        
                        <div class="card-footer">
                            <el-button text bg size="small" @click="viewDetail(ex)">详情</el-button>
                            <el-button type="primary" size="small" icon="VideoPlay" @click="startTraining(ex)">
                                练这个
                            </el-button>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <div class="pagination-container" v-if="totalCount > 0">
            <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[12, 24, 36, 48]"
                layout="total, sizes, prev, pager, next, jumper"
                :total="totalCount"
                @current-change="handlePageChange"
                @size-change="handleSizeChange"
                background
            />
        </div>
        <div class="no-more-data" v-if="exercises.length === 0 && !loading">
            <el-empty description="没有找到符合条件的动作" />
        </div>

        <el-dialog v-model="detailVisible" :title="currentEx.name" width="800px" align-center class="exercise-dialog">
            <div class="detail-content" v-if="currentEx.id">
                <div class="dialog-flex-container">
                    <div class="dialog-left-pane">
                        <div class="dialog-image-wrapper">
                            <img :src="currentEx.image_url" class="dialog-image" />
                        </div>
                        
                        <div class="user-progress-box" v-if="currentEx.user_best_score !== null">
                            <div class="progress-title">📈 历史表现</div>
                            <div class="progress-stats">
                                <div class="p-item">
                                    <span class="p-label">最高准确率</span>
                                    <span class="p-value">{{ (currentEx.user_best_score * 100).toFixed(1) }}%</span>
                                </div>
                                <div class="p-item" v-if="currentEx.user_last_record">
                                    <span class="p-label">最近练习</span>
                                    <span class="p-value">{{ new Date(currentEx.user_last_record.created_at).toLocaleDateString() }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="dialog-right-pane">
                        <div class="dialog-body">
                            <div class="dialog-section">
                                <h4>💡 动作要领</h4>
                                <p class="instructions-text">{{ currentEx.instructions }}</p>
                            </div>
                            
                            <div class="dialog-section">
                                <h4>⚠️ 注意事项</h4>
                                <el-alert :title="currentEx.tips || '保持核心收紧，注意呼吸节奏'" type="warning" :closable="false" show-icon />
                            </div>

                            <div class="dialog-section" v-if="currentEx.correction_tips">
                                <h4>🤖 AI 纠错建议</h4>
                                <ul class="ai-tips">
                                    <li v-for="(tip, key) in currentEx.correction_tips" :key="key">
                                        {{ tip }}
                                    </li>
                                </ul>
                            </div>

                            <div class="dialog-section" v-if="currentEx.prerequisite_list && currentEx.prerequisite_list.length">
                                <h4>📚 前置基础</h4>
                                <div class="relation-tags">
                                    <el-tag v-for="rel in currentEx.prerequisite_list" :key="rel.id" type="info" size="small" class="mr-1 clickable-tag" @click="navigateToExercise(rel.id)">
                                        {{ rel.name }}
                                    </el-tag>
                                </div>
                            </div>

                            <div class="dialog-section" v-if="currentEx.unlocks && currentEx.unlocks.length">
                                <h4>🔓 后后续解锁</h4>
                                <div class="relation-tags">
                                    <el-tag v-for="rel in currentEx.unlocks" :key="rel.id" type="success" size="small" class="mr-1 clickable-tag" @click="navigateToExercise(rel.id)">
                                        {{ rel.name }}
                                    </el-tag>
                                </div>
                            </div>

                            <div class="dialog-stats">
                                <div class="stat-item">
                                    <div class="label">消耗</div>
                                    <div class="value">{{ currentEx.calories_burned }} <small>kcal/min</small></div>
                                </div>
                                <div class="stat-item">
                                    <div class="label">推荐组次</div>
                                    <div class="value">{{ currentEx.default_reps }} <small>次</small></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <template #footer>
                 <span class="dialog-footer">
                    <el-button @click="detailVisible = false">关闭</el-button>
                    <el-button type="primary" @click="startTraining(currentEx)">立即开始训练</el-button>
                </span>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { debounce } from 'lodash-es'
import apiClient from '../api'

const router = useRouter()
const exercises = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const ordering = ref('order')
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const filter = ref({
    target_muscle: '',
    difficulty: '',
    equipment: ''
})

const detailVisible = ref(false)
const currentEx = ref<any>({})

// 初始加载或筛选改变时调用
const fetchExercises = async () => {
    loading.value = true
    
    try {
        const params: any = {
            page: currentPage.value,
            page_size: pageSize.value,
            ordering: ordering.value
        }
        
        if (filter.value.target_muscle) params.target_muscle = filter.value.target_muscle
        if (filter.value.difficulty) params.difficulty = filter.value.difficulty
        if (filter.value.equipment) params.equipment = filter.value.equipment
        
        if (search.value) {
            params.search = search.value
        }
        
        const res = await apiClient.get('exercises/', { params })

        // 处理分页数据
        if (res.data.results) {
            exercises.value = res.data.results
            totalCount.value = res.data.count
        } else {
            // 如果后端没开启分页（兼容处理）
            exercises.value = res.data
            totalCount.value = res.data.length
        }

    } catch (err) {
        console.error('获取动作失败:', err)
    } finally {
        loading.value = false
    }
}

// 采用 debounce 的搜索，避免频繁请求后端
const debouncedFetch = debounce(() => {
    currentPage.value = 1
    fetchExercises()
}, 500)

// 监听搜索词变化
watch(search, () => {
    debouncedFetch()
})

// 监听筛选条件变化
watch([
    () => filter.value.target_muscle,
    () => filter.value.difficulty,
    () => filter.value.equipment
], () => {
    currentPage.value = 1
    fetchExercises()
})

const handlePageChange = (page: number) => {
    currentPage.value = page
    fetchExercises()
    // 自动滚动到顶部，提升体验
    window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleSizeChange = (size: number) => {
    pageSize.value = size
    currentPage.value = 1
    fetchExercises()
}

const handleSearchClear = () => {
    search.value = ''
    currentPage.value = 1
    fetchExercises()
}

const viewDetail = (ex: any) => {
    currentEx.value = ex
    detailVisible.value = true
}

const navigateToExercise = async (id: number) => {
    try {
        const res = await apiClient.get(`exercises/${id}/`)
        currentEx.value = res.data
        // 保持弹窗开启，但更新内容
    } catch (err) {
        ElMessage.error('无法加载该动作详情')
    }
}

const startTraining = (ex: any) => {
    detailVisible.value = false
    router.push({
        path: '/training',
        query: {
            exercise_id: ex.id,
            exercise_name: ex.name
        }
    })
}

onMounted(() => {
    fetchExercises()
})
</script>

<script lang="ts">
export default {
    name: 'ExercisesView'
}
</script>

<style scoped>
.page-container {
    max-width: 1200px;
    margin: 0 auto;
    padding-bottom: 60px;
}

.page-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
}

.search-input {
    width: 300px;
    border-radius: 8px;
}

.sort-select {
    width: 160px;
    margin-right: 12px;
}

.filter-card {
    margin-bottom: 24px;
    border: none;
    border-radius: 12px;
    box-shadow: var(--card-shadow, 0 4px 12px rgba(0,0,0,0.05));
    background: #fff;
}

.filter-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.filter-row {
    display: flex;
    align-items: center;
    gap: 16px;
}

.mt-2 {
    margin-top: 8px;
}

.filter-label {
    font-weight: 600;
    color: var(--text-secondary);
    min-width: 80px;
}

.custom-radio-group :deep(.el-radio-button__inner) {
    border: none;
    background: transparent;
    padding: 8px 16px;
    border-radius: 6px;
    margin-right: 4px;
    color: var(--text-secondary);
}

.custom-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    background-color: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    box-shadow: none;
    font-weight: 600;
}

/* Exercise Card */
.exercise-card {
    border: none;
    border-radius: 16px;
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.hover-lift:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1);
}

.card-image-wrapper {
    position: relative;
    height: 180px;
    overflow: hidden;
    background: #1f2937; 
    display: flex;      
    align-items: center;
    justify-content: center;
}

.image {
    width: 60%;         
    height: 60%;
    object-fit: contain; 
    transition: transform 0.5s ease;
    filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3)); 
}

.exercise-card:hover .image {
    transform: scale(1.1);
}

.difficulty-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    color: white;
    backdrop-filter: blur(4px);
    text-transform: uppercase;
}
.difficulty-badge.beginner { background: rgba(16, 185, 129, 0.9); }
.difficulty-badge.intermediate { background: rgba(245, 158, 11, 0.9); }
.difficulty-badge.advanced { background: rgba(239, 68, 68, 0.9); }

.card-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    flex: 1;
}

.title-row {
    margin-bottom: 8px;
}

.title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-main);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.tags-row {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
}

.desc {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0 0 16px 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    height: 40px; 
}

.card-footer {
    margin-top: auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Pagination / Load More */
.pagination-container {
    margin-top: 10px;
    margin-bottom: 40px;
    display: flex;
    justify-content: center;
}

.no-more-data {
    text-align: center;
    color: var(--text-secondary);
    margin-top: 20px;
    padding-bottom: 20px;
}

/* Dialog */
.exercise-dialog :deep(.el-dialog__body) {
    padding: 0; /* 移除默认内边距，实现图片贴合 */
    overflow: hidden;
}

.dialog-flex-container {
    display: flex;
    min-height: 400px;
}

.dialog-left-pane {
    flex: 0 0 320px;
    background: #1f2937;
    display: flex;
    flex-direction: column;
}

.dialog-right-pane {
    flex: 1;
    padding: 24px;
    background: #fff;
}

.dialog-image-wrapper {
    width: 100%;
    height: 320px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.dialog-image {
    width: 100%;
    height: 100%;
    object-fit: contain; /* 默认 contain 保证不裁剪，背景色填充 */
    padding: 20px; /* 内部稍微留白，避免主体图片贴边太死 */
}

.dialog-image-wrapper:hover .dialog-image {
    transform: scale(1.05);
}

.user-progress-box {
    margin: auto 16px 16px 16px; /* 移动到左侧窗格底部 */
    padding: 12px;
    background: rgba(255, 255, 255, 0.05); /* 深色背景下的进度框 */
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.progress-title {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 8px;
}

.progress-stats {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.p-item {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
}

.p-label {
    color: #9ca3af;
}

.p-value {
    font-weight: 600;
    color: #fff;
}

.ai-tips {
    margin: 0;
    padding-left: 18px;
    color: #606266;
    font-size: 14px;
    line-height: 1.6;
}

.ai-tips li {
    margin-bottom: 4px;
}

.dialog-section {
    margin-bottom: 20px;
}

.instructions-text {
    white-space: pre-line; /* 让换行符生效 */
}

.dialog-section h4 {
    margin: 0 0 8px 0;
    font-size: 15px;
    color: var(--text-main);
    font-weight: 700;
}

.dialog-section p {
    color: var(--text-secondary);
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
}

.dialog-stats {
    display: flex;
    gap: 30px;
    background: var(--bg-color);
    padding: 16px;
    border-radius: 12px;
}

.relation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}

.clickable-tag {
    cursor: pointer;
    transition: all 0.2s;
}

.clickable-tag:hover {
    transform: scale(1.05);
    opacity: 0.8;
}

.stat-item .label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.stat-item .value {
    font-size: 20px;
    font-weight: 700;
    color: var(--el-color-primary);
}

.stat-item .value small {
    font-size: 12px;
    font-weight: 400;
    color: var(--text-secondary);
}
</style>
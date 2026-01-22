<template>
    <div class="page-container">
        <div class="page-header-row">
            <h1 class="page-title">动作百科</h1>
            <div class="header-actions">
                <el-input v-model="search" placeholder="搜索动作名称..." size="large" class="search-input" clearable @clear="handleSearchClear">
                    <template #prefix>
                        <el-icon class="search-icon"><Search /></el-icon>
                    </template>
                </el-input>
            </div>
        </div>

        <el-card class="filter-card mb-4" :body-style="{ padding: '12px 20px' }">
            <div class="filter-row">
                <span class="filter-label">部位筛选:</span>
                <el-radio-group v-model="filter.target_muscle" size="default" @change="fetchExercises" class="custom-radio-group">
                    <el-radio-button label="">全部</el-radio-button>
                    <el-radio-button label="chest">胸部</el-radio-button>
                    <el-radio-button label="back">背部</el-radio-button>
                    <el-radio-button label="shoulders">肩部</el-radio-button>
                    <el-radio-button label="arms">手臂</el-radio-button>
                    <el-radio-button label="abs">腹部</el-radio-button>
                    <el-radio-button label="legs">腿部</el-radio-button>
                </el-radio-group>
            </div>
        </el-card>

        <el-row :gutter="24" v-loading="loading">
            <el-col v-for="ex in filteredExercises" :key="ex.id" :xs="24" :sm="12" :md="8" :lg="6">
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
                            <el-tag size="small" type="info" effect="plain" round>🛠️ {{ ex.equipment_display }}</el-tag>
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

        <div class="pagination-container" v-if="nextUrl">
            <el-button 
                type="primary" 
                plain 
                round 
                size="large"
                :loading="loadingMore" 
                @click="loadMore"
            >
                加载更多动作 ({{ exercises.length }} / {{ totalCount }})
            </el-button>
        </div>
        <div class="no-more-data" v-else-if="exercises.length > 0 && !loading">
            <small>没有更多动作了</small>
        </div>

        <el-dialog v-model="detailVisible" :title="currentEx.name" width="600px" align-center class="exercise-dialog">
            <div class="detail-content" v-if="currentEx.id">
                <div class="dialog-image-wrapper">
                    <img :src="currentEx.image_url" class="dialog-image" />
                </div>
                
                <div class="dialog-body">
                    <div class="dialog-section">
                        <h4>💡 动作要领</h4>
                        <p class="instructions-text">{{ currentEx.instructions }}</p>
                    </div>
                    
                    <div class="dialog-section">
                        <h4>⚠️ 注意事项</h4>
                        <el-alert :title="currentEx.tips || '保持核心收紧，注意呼吸节奏'" type="warning" :closable="false" show-icon />
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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, VideoPlay } from '@element-plus/icons-vue'
import apiClient from '../api'

const router = useRouter()
const exercises = ref<any[]>([])
const loading = ref(false)
const loadingMore = ref(false) // 加载更多时的loading
const search = ref('')
const nextUrl = ref<string | null>(null) // 下一页的URL
const totalCount = ref(0) // 总数
const filter = ref({
    target_muscle: ''
})

const detailVisible = ref(false)
const currentEx = ref<any>({})

// 初始加载或筛选改变时调用
const fetchExercises = async () => {
    loading.value = true
    // 重置列表
    exercises.value = []
    nextUrl.value = null
    
    try {
        let url = 'exercises/'
        if (filter.value.target_muscle) {
            url += `?target_muscle=${filter.value.target_muscle}`
        }
        
        const res = await apiClient.get(url)

        // 处理分页数据
        if (res.data.results) {
            exercises.value = res.data.results
            nextUrl.value = res.data.next // 记录下一页
            totalCount.value = res.data.count // 记录总数
        } else {
            // 如果后端没开启分页（兼容处理）
            exercises.value = res.data
            nextUrl.value = null
        }

    } catch (err) {
        console.error(err)
    } finally {
        loading.value = false
    }
}

// 加载更多按钮点击时调用
const loadMore = async () => {
    if (!nextUrl.value) return
    
    loadingMore.value = true
    try {
        // 直接请求 nextUrl
        // 注意：nextUrl 是完整链接 (http://...), apiClient.get 会处理
        const res = await apiClient.get(nextUrl.value)
        
        if (res.data.results) {
            // 关键：将新数据追加到现有数组后面
            exercises.value.push(...res.data.results)
            // 更新下一页地址
            nextUrl.value = res.data.next
        }
    } catch (err) {
        console.error("加载更多失败", err)
    } finally {
        loadingMore.value = false
    }
}

const filteredExercises = computed(() => {
    if (!search.value) return exercises.value
    // 注意：这里的搜索只针对“已加载”的数据进行过滤
    return exercises.value.filter(ex => 
        ex.name.toLowerCase().includes(search.value.toLowerCase()) ||
        ex.english_name?.toLowerCase().includes(search.value.toLowerCase())
    )
})

const handleSearchClear = () => {
    search.value = ''
}

const viewDetail = (ex: any) => {
    currentEx.value = ex
    detailVisible.value = true
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

.filter-card {
    margin-bottom: 24px;
    border: none;
    border-radius: 12px;
    box-shadow: var(--card-shadow);
}

.filter-row {
    display: flex;
    align-items: center;
    gap: 16px;
}

.filter-label {
    font-weight: 600;
    color: var(--text-secondary);
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
.dialog-image-wrapper {
    margin: -20px -20px 20px -20px;
    height: 240px;
    overflow: hidden;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
}

.dialog-image {
    width: 100%;
    height: 100%;
    object-fit: contain; /* 修复详情弹窗图片变形问题 */
    max-width: 300px;
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
<template>
    <div class="exercises-container">
        <el-card>
            <template #header>
                <div class="header">
                    <span>📖 动作百科</span>
                    <el-input v-model="search" placeholder="搜索动作名称..." style="width: 250px" clearable>
                        <template #prefix>
                            <el-icon>
                                <Search />
                            </el-icon>
                        </template>
                    </el-input>
                </div>
            </template>

            <div class="filter-section">
                <el-radio-group v-model="filter.target_muscle" size="small" @change="fetchExercises">
                    <el-radio-button label="">全部部位</el-radio-button>
                    <el-radio-button label="chest">胸部</el-radio-button>
                    <el-radio-button label="back">背部</el-radio-button>
                    <el-radio-button label="shoulders">肩部</el-radio-button>
                    <el-radio-button label="arms">手臂</el-radio-button>
                    <el-radio-button label="abs">腹部</el-radio-button>
                    <el-radio-button label="legs">腿部</el-radio-button>
                </el-radio-group>
            </div>

            <el-row :gutter="20" v-loading="loading">
                <el-col v-for="ex in filteredExercises" :key="ex.id" :xs="24" :sm="12" :md="8" :lg="6">
                    <el-card class="exercise-card" shadow="hover">
                        <img :src="ex.image_url || 'https://via.placeholder.com/300x200?text=FitVision'"
                            class="image" />
                        <div style="padding: 14px">
                            <div class="title-row">
                                <span class="title">{{ ex.name }}</span>
                                <el-tag size="small" :type="getDifficultyType(ex.difficulty)">{{ ex.difficulty_display
                                }}</el-tag>
                            </div>
                            <div class="info-row">
                                <span class="muscle">🎯 {{ ex.target_muscle_display }}</span>
                                <span class="equipment">🛠️ {{ ex.equipment_display }}</span>
                            </div>
                            <p class="desc">{{ ex.description }}</p>
                            <div class="bottom">
                                <el-button type="primary" link @click="viewDetail(ex)">查看详情</el-button>
                                <el-button type="success" size="small" @click="startTraining(ex)">开始训练</el-button>
                            </div>
                        </div>
                    </el-card>
                </el-col>
            </el-row>
        </el-card>

        <!-- 动作详情弹窗 -->
        <el-dialog v-model="detailVisible" :title="currentEx.name" width="60%">
            <div class="detail-content" v-if="currentEx.id">
                <el-row :gutter="20">
                    <el-col :span="10">
                        <img :src="currentEx.image_url" style="width: 100%; border-radius: 8px" />
                    </el-col>
                    <el-col :span="14">
                        <h4>动作要领</h4>
                        <p>{{ currentEx.instructions }}</p>
                        <h4>注意事项</h4>
                        <p class="tips">{{ currentEx.tips || '暂无注意事项' }}</p>
                        <div class="ai-params">
                            <el-tag type="info">每分钟消耗: {{ currentEx.calories_burned }} kcal</el-tag>
                            <el-tag type="success">推荐每组: {{ currentEx.default_reps }} 次</el-tag>
                        </div>
                    </el-col>
                </el-row>
            </div>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import apiClient from '../api'

const router = useRouter()
const exercises = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const filter = ref({
    target_muscle: ''
})

const detailVisible = ref(false)
const currentEx = ref<any>({})

const fetchExercises = async () => {
    loading.value = true
    try {
        let url = 'exercises/'
        if (filter.value.target_muscle) {
            url += `?target_muscle=${filter.value.target_muscle}`
        }
        const res = await apiClient.get(url)
        exercises.value = res.data
    } catch (err) {
        console.error(err)
    } finally {
        loading.value = false
    }
}

const filteredExercises = computed(() => {
    if (!search.value) return exercises.value
    return exercises.value.filter(ex =>
        ex.name.toLowerCase().includes(search.value.toLowerCase()) ||
        ex.english_name?.toLowerCase().includes(search.value.toLowerCase())
    )
})

const getDifficultyType = (diff: string) => {
    if (diff === 'beginner') return 'success'
    if (diff === 'intermediate') return 'warning'
    return 'danger'
}

const viewDetail = (ex: any) => {
    currentEx.value = ex
    detailVisible.value = true
}

const startTraining = (ex: any) => {
    // 跳转到训练页面并带上动作 ID 和名称
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
.exercises-container {
    padding: 20px;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.filter-section {
    margin-bottom: 20px;
}

.exercise-card {
    margin-bottom: 20px;
    height: 100%;
}

.image {
    width: 100%;
    height: 200px;
    object-fit: cover;
}

.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.title {
    font-size: 16px;
    font-weight: bold;
}

.info-row {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
}

.desc {
    font-size: 13px;
    color: #606266;
    height: 40px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.bottom {
    margin-top: 13px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.tips {
    color: #e6a23c;
    font-style: italic;
}

.ai-params {
    margin-top: 15px;
    display: flex;
    gap: 10px;
}
</style>

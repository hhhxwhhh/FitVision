<template>
  <div class="next-up-card" v-if="recommendations.length > 0">
    <div class="header">
      <div class="title">
        <el-icon class="icon"><Sort /></el-icon>
        <span>AI 智能接力</span>
      </div>
      <el-tag size="small" type="success" effect="dark">序列预测</el-tag>
    </div>
    
    <p class="subtitle">练完这组，AI 建议您接下来尝试：</p>
    
    <div class="rec-list">
      <div v-for="rec in recommendations" :key="rec.id" class="mini-rec-item" @click="selectExercise(rec.exercise)">
        <el-image :src="rec.exercise.image_url || '/placeholder.jpg'" class="thumb" fit="cover" />
        <div class="info">
          <div class="name">{{ rec.exercise.name }}</div>
          <div class="reason">{{ rec.reason }}</div>
        </div>
        <el-button type="primary" link icon="ArrowRight" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Sort } from '@element-plus/icons-vue'
import apiClient from '../api'

const props = defineProps<{
  lastExerciseId?: string | number
}>()

const emit = defineEmits(['select'])

const recommendations = ref<any[]>([])
const loading = ref(false)

const fetchNextUp = async () => {
  if (!props.lastExerciseId) return
  loading.value = true
  try {
    // 使用 default 场景，后端会根据是否有交互历史自动切换到 dl_sequence
    const res = await apiClient.get('/recommendations/list/get_personalized/?scenario=default&limit=2')
    recommendations.value = res.data
  } catch (err) {
    console.error('Next up fetch failed', err)
  } finally {
    loading.value = false
  }
}

const selectExercise = (ex: any) => {
  emit('select', ex)
}

watch(() => props.lastExerciseId, () => {
  fetchNextUp()
})

onMounted(() => {
  if (props.lastExerciseId) fetchNextUp()
})
</script>

<style scoped>
.next-up-card {
  margin-top: 20px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #bae6fd;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.title {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #0369a1;
}

.icon {
  margin-right: 8px;
  font-size: 18px;
}

.subtitle {
  font-size: 13px;
  color: #0c4a6e;
  margin-bottom: 15px;
}

.rec-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mini-rec-item {
  display: flex;
  align-items: center;
  background: white;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}

.mini-rec-item:hover {
  transform: translateX(5px);
}

.thumb {
  width: 45px;
  height: 45px;
  border-radius: 6px;
  margin-right: 12px;
}

.info {
  flex: 1;
}

.name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}

.reason {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}
</style>

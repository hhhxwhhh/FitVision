<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title">个人中心</h1>
      <el-button type="primary" size="large" @click="handleSave" :loading="loading" :disabled="!isFormChanged" class="save-btn shadow-btn">
        保存修改
      </el-button>
    </div>

    <el-row :gutter="24">
      <el-col :md="24" :lg="16" class="col-left">
        <el-card class="profile-card">
          <template #header>
            <div class="card-header-styled">
              <h3>📝 基本资料</h3>
            </div>
          </template>

          <el-form label-position="top" :model="form" ref="formRef" class="profile-form">
            <el-row :gutter="24">
              <el-col :span="16">
                <el-form-item label="昵称">
                  <el-input v-model="form.nickname" placeholder="给自己起个名字" maxlength="50" size="large">
                     <template #prefix>
                        <el-icon><User /></el-icon>
                     </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="性别">
                  <el-select v-model="form.gender" size="large" style="width: 100%">
                    <el-option label="男" value="male" />
                    <el-option label="女" value="female" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="8">
                 <el-form-item label="年龄">
                  <el-input-number v-model="form.age" :min="1" :max="120" style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="身高 (cm)">
                  <el-input-number v-model="form.height" :min="100" :max="250" controls-position="right"
                    style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="体重 (kg)">
                  <el-input-number v-model="form.weight" :min="30" :max="200" controls-position="right"
                    style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="运动基础">
              <el-radio-group v-model="form.fitness_level" size="large" class="level-radio-group">
                <el-radio-button label="beginner">新手 (小白)</el-radio-button>
                <el-radio-button label="intermediate">进阶 (有经验)</el-radio-button>
                <el-radio-button label="advanced">大神 (专业)</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="伤病历史">
               <el-input v-model="form.injury_history" type="textarea" 
                    placeholder="无伤病填'无'。AI 教练会根据此信息为您规避高风险动作，请如实填写。"
                    :autosize="{ minRows: 4, maxRows: 6 }" 
                    class="styled-textarea"
                />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :md="24" :lg="8" class="col-right">
        <!-- Body Metrics Card -->
        <el-card class="metrics-card">
          <div class="metrics-header">
             <h3>身体指标解析</h3>
             <el-tag effect="plain" round>AI Calculated</el-tag>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">BMI 体质指数</div>
            <div class="metric-value-row">
               <div class="metric-value">{{ computedBMI.toFixed(1) }}</div>
               <el-tag :type="getBMIType(computedBMI)" effect="dark" round>
                  {{ getBMIText(computedBMI) }}
               </el-tag>
            </div>
            <el-progress :percentage="Math.min(computedBMI * 2.5, 100)" :color="getBMIColor(computedBMI)" :show-text="false" stroke-width="6" class="mt-2" />
          </div>

          <div class="metric-divider"></div>

          <div class="metric-item">
             <div class="metric-label">BMR 基础代谢</div>
             <div class="metric-value-row">
                <div class="metric-value">{{ Math.round(computedBMR) }} <span class="unit">kcal/day</span></div>
             </div>
             <p class="metric-desc">即使整天躺着不动，身体维持生命所需的最低热量消耗。</p>
          </div>

          <div class="metric-divider"></div>

          <div class="info-section">
             <el-alert title="关于您的数据" type="info" :closable="false" show-icon>
               您的身体数据将直接决定训练强度和推荐计划。请定期更新以获得最佳体验。
             </el-alert>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import type { FormInstance } from 'element-plus'
import apiClient from '../api'

const loading = ref(false)
const formRef = ref<FormInstance>()
const isFormChanged = ref(false)

const form = reactive({
  nickname: '',
  gender: 'male' as 'male' | 'female',
  age: 25,
  height: 170,
  weight: 65,
  fitness_level: 'beginner',
  injury_history: ''
})

let originalFormStr = ''

const computedBMI = computed(() => {
  if (!form.height || !form.weight) return 0
  return form.weight / ((form.height / 100) * (form.height / 100))
})

const computedBMR = computed(() => {
  if (!form.weight || !form.height || !form.age) return 0
  if (form.gender === 'male') {
    return 10 * form.weight + 6.25 * form.height - 5 * form.age + 5
  } else {
    return 10 * form.weight + 6.25 * form.height - 5 * form.age - 161
  }
})

const getBMIType = (bmi: number) => {
  if (bmi < 18.5) return 'warning'
  if (bmi < 24) return 'success'
  if (bmi < 28) return 'warning'
  return 'danger'
}

const getBMIColor = (bmi: number) => {
  if (bmi < 18.5) return '#e6a23c'
  if (bmi < 24) return '#67c23a'
  if (bmi < 28) return '#e6a23c'
  return '#f56c6c'
}

const getBMIText = (bmi: number) => {
  if (bmi < 18.5) return '偏瘦'
  if (bmi < 24) return '正常'
  if (bmi < 28) return '超重'
  return '肥胖'
}

watch(form, () => {
  isFormChanged.value = JSON.stringify(form) !== originalFormStr
}, { deep: true })

onMounted(async () => {
  loading.value = true
  try {
    const res = await apiClient.get('auth/profile/')
    Object.assign(form, res.data)
    originalFormStr = JSON.stringify(form)
    isFormChanged.value = false
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '无法获取个人资料')
  } finally {
    loading.value = false
  }
})

const handleSave = async () => {
  loading.value = true
  try {
    const res = await apiClient.put('auth/profile/', form)
    Object.assign(form, res.data)
    originalFormStr = JSON.stringify(form)
    isFormChanged.value = false
    ElMessage.success('保存成功！AI 已更新你的身体参数')
  } catch (err: any) {
    ElMessage.error('保存失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 60px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.profile-card {
  border-radius: 16px;
  border: none;
  overflow: hidden;
  box-shadow: var(--card-shadow);
}

.card-header-styled {
    padding: 12px 0;
    border-bottom: 2px solid var(--border-color);
    margin-bottom: 24px;
}

.card-header-styled h3 {
    margin: 0;
    font-size: 18px;
    color: var(--text-main);
}

.profile-form :deep(.el-form-item__label) {
    font-weight: 500;
}

.level-radio-group {
    width: 100%;
}

.level-radio-group :deep(.el-radio-button__inner) {
    width: 33.33%;
    border-radius: 0;
}

.level-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
    border-radius: 8px 0 0 8px;
}
.level-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
    border-radius: 0 8px 8px 0;
}

.save-btn {
    font-weight: 600;
}

.shadow-btn {
    box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.4);
}

/* Right Col Metrics */
.metrics-card {
   background: #334155; 
   color: white;
   border: none;
   border-radius: 16px;
}

.metrics-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}

.metrics-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #f8fafc;
}

.metric-item {
    margin-bottom: 24px;
}

.metric-label {
    font-size: 14px;
    color: #94a3b8;
    margin-bottom: 8px;
}

.metric-value-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
}

.metric-value {
    font-size: 36px;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1;
}

.metric-value .unit {
    font-size: 14px;
    color: #94a3b8;
    font-weight: 400;
}

.metric-desc {
    font-size: 13px;
    color: #cbd5e1;
    margin-top: 8px;
    line-height: 1.5;
}

.metric-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 24px 0;
}

.mt-2 {
    margin-top: 12px;
}

.col-right {
    margin-top: 24px;
}

@media (min-width: 992px) {
    .col-right {
        margin-top: 0;
    }
}
</style>
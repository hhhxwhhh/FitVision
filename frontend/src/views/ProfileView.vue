<template>
  <div class="profile-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>👤 个人档案</span>
          <el-button type="primary" @click="handleSave" :loading="loading" :disabled="!isFormChanged">
            保存修改
          </el-button>
        </div>
      </template>

      <el-form label-width="100px" :model="form" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item label="昵称">
              <el-input v-model="form.nickname" placeholder="给自己起个名字" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年龄">
              <el-input-number v-model="form.age" :min="1" :max="120" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio label="male">男</el-radio>
            <el-radio label="female">女</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="身高 (cm)">
              <el-input-number v-model="form.height" :min="100" :max="250" controls-position="right"
                style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="体重 (kg)">
              <el-input-number v-model="form.weight" :min="30" :max="200" controls-position="right"
                style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">身体指标 (系统自动计算)</el-divider>
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="12">
            <el-statistic title="BMI (体质指数)" :value="computedBMI || 0" :precision="1">
              <template #suffix>
                <el-tag :type="getBMIType(computedBMI)" size="small" style="margin-left: 5px">
                  {{ getBMIText(computedBMI) }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="12">
            <el-statistic title="BMR (基础代谢率)" :value="computedBMR || 0">
              <template #suffix> kcal/day</template>
            </el-statistic>
          </el-col>
        </el-row>

        <el-form-item label="运动基础">
          <el-select v-model="form.fitness_level" placeholder="请选择" style="width: 100%">
            <el-option label="新手 (小白)" value="beginner" />
            <el-option label="进阶 (有经验)" value="intermediate" />
            <el-option label="大神 (专业)" value="advanced" />
          </el-select>
        </el-form-item>

        <el-form-item label="伤病史">
          <el-input v-model="form.injury_history" type="textarea" placeholder="无伤病填'无'，这很重要，AI 会据此避开危险动作"
            :autosize="{ minRows: 3, maxRows: 6 }" />
        </el-form-item>
      </el-form>

      <div style="margin-top: 20px; text-align: center;">
        <el-button @click="$router.push('/')">🔙 返回首页</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
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
.profile-container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .profile-container {
    padding: 10px;
  }
}
</style>
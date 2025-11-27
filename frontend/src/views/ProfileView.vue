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
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="给自己起个名字" maxlength="50" />
        </el-form-item>

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
import { ref, reactive, onMounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'

const loading = ref(false)
const formRef = ref<FormInstance>()
const isFormChanged = ref(false)

const originalForm = reactive({
  nickname: '',
  gender: 'male',
  height: 170,
  weight: 65,
  fitness_level: 'beginner',
  injury_history: ''
})

const form = reactive({
  nickname: '',
  gender: 'male',
  height: 170,
  weight: 65,
  fitness_level: 'beginner',
  injury_history: ''
})

const API_URL = 'http://127.0.0.1:8000/api/auth/profile/'

watch(form, () => {
  isFormChanged.value = JSON.stringify(form) !== JSON.stringify(originalForm)
}, { deep: true })

onMounted(async () => {
  try {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      ElMessage.error('未检测到登录信息，请重新登录')
      return
    }

    const res = await axios.get(API_URL, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    Object.assign(form, res.data)
    Object.assign(originalForm, res.data)
    isFormChanged.value = false
  } catch (err: any) {
    const errorMsg = err.response?.status === 401
      ? '登录已过期，请重新登录'
      : '获取档案失败'
    ElMessage.error(errorMsg)

    if (err.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      setTimeout(() => {
        window.location.href = '/login'
      }, 1500)
    }
  }
})

const handleSave = async () => {
  if (!formRef.value) return

  loading.value = true
  try {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      ElMessage.error('未检测到登录信息，请重新登录')
      return
    }

    await axios.put(API_URL, form, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    Object.assign(originalForm, form)
    isFormChanged.value = false
    ElMessage.success('保存成功！AI 已更新你的身体参数')
  } catch (err: any) {
    const errorMsg = err.response?.status === 401
      ? '登录已过期，请重新登录'
      : '保存失败'
    ElMessage.error(errorMsg)

    if (err.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      setTimeout(() => {
        window.location.href = '/login'
      }, 1500)
    }
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
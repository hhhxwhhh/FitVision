<template>
  <div class="profile-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>👤 个人档案</span>
          <el-button type="primary" @click="handleSave" :loading="loading">保存修改</el-button>
        </div>
      </template>

      <el-form label-width="100px">
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="给自己起个名字" />
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
              <el-input-number v-model="form.height" :min="100" :max="250" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="体重 (kg)">
              <el-input-number v-model="form.weight" :min="30" :max="200" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="运动基础">
          <el-select v-model="form.fitness_level" placeholder="请选择">
            <el-option label="新手 (小白)" value="beginner" />
            <el-option label="进阶 (有经验)" value="intermediate" />
            <el-option label="大神 (专业)" value="advanced" />
          </el-select>
        </el-form-item>

        <el-form-item label="伤病史">
          <el-input v-model="form.injury_history" type="textarea" placeholder="无伤病填'无'，这很重要，AI 会据此避开危险动作" />
        </el-form-item>
      </el-form>
      
      <div style="margin-top: 20px; text-align: center;">
         <el-button @click="$router.push('/')">🔙 返回首页</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const form = reactive({
  nickname: '',
  gender: 'male',
  height: 170,
  weight: 65,
  fitness_level: 'beginner',
  injury_history: ''
})

// 后端地址
const API_URL = 'http://127.0.0.1:8000/api/auth/profile/'

// 1. 进页面先查数据
onMounted(async () => {
  try {
    const token = localStorage.getItem('jwt_token')
    // 注意：所有需要权限的请求，都要带上 Authorization 头
    const res = await axios.get(API_URL, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    // 把后端返回的数据填到表单里
    Object.assign(form, res.data)
  } catch (err) {
    ElMessage.error('获取档案失败，请确保已登录')
  }
})

// 2. 保存数据
const handleSave = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('jwt_token')
    await axios.put(API_URL, form, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    ElMessage.success('保存成功！AI 已更新你的身体参数')
  } catch (err) {
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-container { padding: 20px; max-width: 600px; margin: 0 auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
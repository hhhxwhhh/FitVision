<template>
  <div class="home-container">
    <h1>🏋️‍♂️ FitVision 智能健身</h1>
    <p>欢迎你，{{ username }}</p>

    <div class="menu-grid">
      <el-card class="menu-item" shadow="hover" @click="$router.push('/profile')">
        <h3>👤 完善档案</h3>
        <p>设置身高体重，让 AI 更懂你</p>
      </el-card>

      <el-card class="menu-item highlight" shadow="hover">
        <h3>🚀 开始训练</h3>
        <p>AI 视觉识别深蹲 (开发中)</p>
      </el-card>
      
      <el-card class="menu-item" shadow="hover">
        <h3>📊 训练记录</h3>
        <p>查看历史成就 (待开发)</p>
      </el-card>
    </div>
    
    <el-button type="danger" style="margin-top: 50px" @click="logout">退出登录</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '用户')

const logout = () => {
  localStorage.clear() // 清空 Token
  router.push('/login')
}
</script>

<style scoped>
.home-container { padding: 40px; text-align: center; color: white; }
.menu-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
  gap: 20px; 
  margin-top: 40px; 
}
.menu-item { cursor: pointer; text-align: left; }
.menu-item:hover { transform: translateY(-5px); transition: 0.3s; }
.highlight { border: 2px solid #409EFF; }
</style>
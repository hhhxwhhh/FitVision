<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from './stores/userStore'
import axios from 'axios'

interface ApiResponse {
  message: string;
  status: string;
}

const userStore = useUserStore()
const backendResponse = ref<ApiResponse | null>(null)
const loading = ref(true)
const error = ref<Error | null>(null)
const username = ref('')
const password = ref('')

const fetchData = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/test/')
    backendResponse.value = response.data
    loading.value = false
  } catch (err) {
    error.value = err as Error
    loading.value = false
  }
}

const handleLogin = async () => {
  try {
    await userStore.login({
      username: username.value,
      password: password.value
    })
  } catch (err) {
    console.error('Login failed:', err)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <h1>FitVision 健身追踪</h1>

    <div v-if="userStore.isAuthenticated">
      <p>欢迎, {{ userStore.userName }}!</p>
      <button @click="userStore.logout">退出登录</button>
    </div>

    <div v-else>
      <div>
        <h2>用户登录</h2>
        <input v-model="username" placeholder="用户名" />
        <input v-model="password" type="password" placeholder="密码" />
        <button @click="handleLogin">登录</button>
      </div>

      <h2>前后端通信测试</h2>

      <div v-if="loading">
        正在连接后端...
      </div>

      <div v-else-if="error">
        错误: {{ error.message }}
      </div>

      <div v-else>
        <h3>后端响应:</h3>
        <pre>{{ JSON.stringify(backendResponse, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 {
  color: #2c3e50;
}

div {
  text-align: center;
  margin-top: 50px;
}

input {
  display: block;
  margin: 10px auto;
  padding: 8px;
  width: 200px;
}

button {
  padding: 10px 20px;
  margin: 10px;
  background-color: #42b883;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #359c6d;
}

pre {
  text-align: left;
  background-color: #f4f4f4;
  padding: 20px;
  border-radius: 5px;
  margin: 20px auto;
  width: 50%;
}
</style>
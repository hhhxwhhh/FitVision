<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface ApiResponse {
  message: string;
  status: string;
}

const backendResponse = ref<ApiResponse | null>(null)
const loading = ref(true)
const error = ref<Error | null>(null)

const fetchData = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/test/')
    backendResponse.value = await response.json()
    loading.value = false
  } catch (err) {
    error.value = err as Error
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <h1>FitVision 前后端通信测试</h1>

    <div v-if="loading">
      正在连接后端...
    </div>

    <div v-else-if="error">
      错误: {{ error.message }}
    </div>

    <div v-else>
      <h2>后端响应:</h2>
      <pre>{{ JSON.stringify(backendResponse, null, 2) }}</pre>
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

pre {
  text-align: left;
  background-color: #f4f4f4;
  padding: 20px;
  border-radius: 5px;
  margin: 20px auto;
  width: 50%;
}
</style>
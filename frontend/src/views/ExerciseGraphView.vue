<template>
  <div class="graph-container" v-loading="loading">
    <div class="graph-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" circle @click="router.back()" />
        <h1 class="page-title">动作知识图谱</h1>
      </div>
      <div class="header-tips">
        <el-tag type="info" effect="plain">💡 提示：按住拖动节点，滚轮缩放，蓝色线条表示前置要求关系</el-tag>
      </div>
    </div>

    <el-card class="graph-card" v-loading="loading">
      <div v-show="nodesCount > 0" ref="chartRef" class="chart-box"></div>
      <div v-if="!loading && nodesCount === 0" class="empty-state">
        <el-empty description="暂无图谱数据" />
      </div>
    </el-card>

    <!-- 节点详情弹窗 -->
    <el-dialog v-model="nodeDialogVisible" :title="currentNode.name" width="400px">
      <div v-if="currentNode.id" class="node-detail">
        <div class="detail-item">
          <span class="label">所属部位：</span>
          <el-tag size="small">{{ currentNode.category_name || currentNode.category }}</el-tag>
        </div>
        <div class="detail-item">
          <span class="label">动作难度：</span>
          <el-rate v-model="currentNode.value" disabled />
        </div>
        <div class="detail-item" v-if="currentNode.tags && currentNode.tags.length">
          <span class="label">动作标签：</span>
          <div class="tag-list">
            <el-tag v-for="tag in currentNode.tags" :key="tag" size="small" type="success" effect="light">{{ tag }}</el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="goToExercise(currentNode.id)">查看百科详情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import apiClient from '../api'

const router = useRouter()
const chartRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const nodeDialogVisible = ref(false)
const currentNode = ref<any>({})
const nodesCount = ref(0)
let myChart: any = null

const fetchGraphData = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('exercises/graph/')
    nodesCount.value = res.data.nodes?.length || 0
    if (nodesCount.value > 0) {
      // 等待 DOM 更新（loading 变 false 后的渲染）
      await nextTick()
      initChart(res.data)
    }
  } catch (err) {
    console.error('获取图谱失败', err)
  } finally {
    loading.value = false
    // 再次确认 resize
    setTimeout(() => {
      myChart?.resize()
    }, 200)
  }
}

const initChart = (data: any) => {
  if (!chartRef.value) return
  
  // 提取唯一的部位作为分类
  const categories = Array.from(new Set(data.nodes.map((n: any) => n.category)))
    .map(name => ({ name }))

  // 将节点的 category 转换为索引
  const nodes = data.nodes.map((n: any) => ({
    ...n,
    symbolSize: (n.value || 3) * 15, // 根据难度设置节点大小
    category: categories.findIndex(c => c.name === n.category)
  }))

  // 增强连线数据，添加名称用于 Tooltip 显示
  const links = data.links.map((l: any) => {
    const sourceNode = data.nodes.find((n: any) => n.id === l.source)
    const targetNode = data.nodes.find((n: any) => n.id === l.target)
    return {
      ...l,
      source_name: sourceNode ? sourceNode.name : '',
      target_name: targetNode ? targetNode.name : ''
    }
  })

  myChart = echarts.init(chartRef.value)
  const option = {
    tooltip: {
      show: true,
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `
            <div style="font-weight:bold;margin-bottom:4px;">${params.name}</div>
            <div style="font-size:12px;">部位: ${params.data.category_name || params.data.category}</div>
            <div style="font-size:12px;">难度: ${params.data.value}级</div>
          `
        } else if (params.dataType === 'edge') {
          return `
            <div style="font-size:12px;">
              <b>${params.data.source_name || '前置'}</b> 
              <span style="margin:0 4px;">➔</span> 
              <b>${params.data.target_name || '后继'}</b>
            </div>
          `
        }
        return ''
      }
    },
    legend: {
      data: categories.map(c => c.name),
      orient: 'vertical',
      right: 20,
      top: 20,
      textStyle: { color: '#666' }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: links,
        categories: categories,
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 12,
          color: '#333'
        },
        edgeSymbol: ['none', 'arrow'], // 源节点无装饰，目标节点显示箭头
        edgeSymbolSize: [4, 10], // 箭头大小
        force: {
          initLayout: 'circular', // 初始布局模型，防止节点重叠在 0,0
          repulsion: 1000, // 增加斥力，使节点分布均匀
          edgeLength: [100, 200], // 增加连线长度，使图谱展开
          gravity: 0.1,
          layoutAnimation: true
        },
        draggable: true,
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 5
          }
        },
        lineStyle: {
          color: '#409EFF',
          curveness: 0.2, // 曲线让线条不重叠
          width: 2,
          opacity: 0.5
        }
      }
    ]
  }

  // 为 tooltip 补全显示名称
  nodes.forEach((n: any) => {
    n.category_name = categories[n.category]?.name || '未知'
  })

  myChart.setOption(option)
  
  // 确保初始渲染时正确计算尺寸并自动缩放以适应屏幕
  setTimeout(() => {
    myChart?.resize()
  }, 100)

  myChart.on('click', (params: any) => {
    if (params.dataType === 'node') {
      currentNode.value = params.data
      nodeDialogVisible.value = true
    }
  })
}

const goToExercise = (id: string) => {
  nodeDialogVisible.value = false
  router.push({ path: '/exercises', query: { id } })
}

const handleResize = () => {
  myChart?.resize()
}

onMounted(() => {
  fetchGraphData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  myChart?.dispose()
})
</script>

<style scoped>
.graph-container {
  padding: 20px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.graph-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  overflow: hidden;
  height: 0; /* 强制 flex 生效 */
}

:deep(.el-card__body) {
  flex: 1;
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-box {
  width: 100%;
  flex: 1; /* 使用 flex 而不是百分比高度确保撑满 */
  min-height: 0;
}

.node-detail {
  padding: 10px 0;
}

.detail-item {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.detail-item .label {
  width: 80px;
  color: #909399;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>

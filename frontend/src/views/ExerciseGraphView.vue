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
          <el-rate v-model="currentNode.level_value" disabled />
        </div>
        <div class="detail-item gnn-insight-box" v-if="currentNode.gnn_insight">
          <div class="gnn-label">
            <el-icon><Cpu /></el-icon> GNN 结构洞察
          </div>
          <p class="gnn-text">{{ currentNode.gnn_insight }}</p>
        </div>
        <div class="detail-item" v-if="currentNode.tags && currentNode.tags.length">
          <span class="label">动作标签：</span>
          <div class="tag-list">
            <el-tag v-for="tag in currentNode.tags" :key="tag" size="small" type="success" effect="light">{{ tag }}</el-tag>
          </div>
        </div>
        
        <div class="divider"></div>
        
        <div class="relation-section">
          <div class="rel-group" v-if="currentNode.preds && currentNode.preds.length">
            <div class="rel-header">🔙 前置基础</div>
            <div class="rel-list">
              <el-tag v-for="p in currentNode.preds" :key="p.id" size="small" type="info" class="rel-tag" @click="handleNodeJump(p.id)">
                {{ p.name }}
              </el-tag>
            </div>
          </div>
          
          <div class="rel-group" v-if="currentNode.succs && currentNode.succs.length">
            <div class="rel-header">🔜 后续进阶</div>
            <div class="rel-list">
              <el-tag v-for="s in currentNode.succs" :key="s.id" size="small" type="success" class="rel-tag" @click="handleNodeJump(s.id)">
                {{ s.name }}
              </el-tag>
            </div>
          </div>
          
          <div v-if="(!currentNode.preds || !currentNode.preds.length) && (!currentNode.succs || !currentNode.succs.length)" class="no-rel">
            该动作目前为独立学习节点
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
import { Cpu, ArrowLeft } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import apiClient from '../api'

const router = useRouter()
const chartRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const nodeDialogVisible = ref(false)
const currentNode = ref<any>({})
const nodesCount = ref(0)
let myChart: any = null
let graphRawData: any = null

const handleNodeJump = (id: number) => {
  const node = graphRawData.nodes.find((n: any) => n.id === id)
  if (node) {
    showNodeDetail(node)
  }
}

const showNodeDetail = (node: any) => {
  // 查找前置动作 (links 中 target 是当前 node.id 的)
  const preds = graphRawData.links
    .filter((l: any) => l.target === node.id)
    .map((l: any) => graphRawData.nodes.find((n: any) => n.id === l.source))
    .filter(Boolean)

  // 查找后续动作 (links 中 source 是当前 node.id 的)
  const succs = graphRawData.links
    .filter((l: any) => l.source === node.id)
    .map((l: any) => graphRawData.nodes.find((n: any) => n.id === l.target))
    .filter(Boolean)

  currentNode.value = { 
    ...node, 
    level_value: node.value, // value 其实是 GNN 分分
    preds, 
    succs 
  }
  nodeDialogVisible.value = true
}

const fetchGraphData = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('exercises/graph/')
    graphRawData = res.data
    nodesCount.value = res.data.nodes?.length || 0
    if (nodesCount.value > 0) {
      await nextTick()
      initChart(res.data)
    }
  } catch (err) {
    console.error('获取图谱失败', err)
  } finally {
    loading.value = false
    setTimeout(() => {
      myChart?.resize()
    }, 200)
  }
}

const initChart = (data: any) => {
  if (!chartRef.value) return
  
  // 使用后端提供的 categories
  const categories = data.categories || []

  // 处理节点：保留后端计算好的颜色和大小
  const nodes = data.nodes.map((n: any) => ({
    ...n,
    category: categories.findIndex((c: any) => c.name === n.category)
  }))

  const links = data.links.map((l: any) => {
    const sourceNode = data.nodes.find((n: any) => n.id === l.source)
    const targetNode = data.nodes.find((n: any) => n.id === l.target)
    return {
      ...l,
      source_name: sourceNode ? sourceNode.name : '',
      target_name: targetNode ? targetNode.name : '',
      label: l.label || { show: true, formatter: '前置基础', position: 'middle', fontSize: 10 }
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
      showNodeDetail(params.data)
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

.divider {
  height: 1px;
  background: #ebeef5;
  margin: 15px 0;
}

.relation-section {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.rel-header {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 8px;
}

.rel-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rel-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.rel-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.no-rel {
  text-align: center;
  color: #909399;
  font-style: italic;
  font-size: 13px;
  padding: 10px 0;
}

.gnn-insight-box {
  background: #f0f7ff;
  border-radius: 8px;
  padding: 12px;
  display: block !important; /* 强制覆盖 flex */
  margin: 10px 0;
}

.gnn-label {
  color: #409eff;
  font-weight: bold;
  font-size: 13px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.gnn-text {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
</style>

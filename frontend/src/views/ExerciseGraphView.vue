<template>
  <div class="graph-container" v-loading="loading">
    <div class="graph-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" circle @click="router.back()" />
        <h1 class="page-title">动作知识图谱</h1>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索动作..."
          clearable
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <div v-if="stats" class="progress-stats">
          <span class="stat-item">探索进度: <b>{{ stats.mastered }}/{{ stats.total }}</b></span>
          <el-progress :percentage="stats.percent" :stroke-width="10" striped animated style="width: 120px" :color="progressColor" />
        </div>
      </div>
    </div>
    
    <div class="graph-toolbar">
      <el-tag type="success" effect="dark" class="status-legend"><el-icon><CircleCheck /></el-icon> 已掌握</el-tag>
      <el-tag type="warning" effect="dark" class="status-legend"><el-icon><Promotion /></el-icon> 可开始</el-tag>
      <el-tag type="info" effect="plain" class="status-legend"><el-icon><Lock /></el-icon> 未解锁</el-tag>
      <el-tag type="primary" effect="plain" class="status-legend"><el-icon><Link /></el-icon> 虚线: 进阶路径</el-tag>
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
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Cpu, ArrowLeft, Search, CircleCheck, Promotion, Lock, Link } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import apiClient from '../api'

const router = useRouter()
const chartRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const nodeDialogVisible = ref(false)
const currentNode = ref<any>({})
const nodesCount = ref(0)
const searchQuery = ref('')
const stats = ref<any>(null)
let myChart: any = null
let graphRawData: any = null

const progressColor = computed(() => {
  if (!stats.value) return '#ff4d4f'
  const p = stats.value.percent
  if (p < 30) return '#f56c6c'
  if (p < 70) return '#e6a23c'
  return '#67c23a'
})

const handleSearch = () => {
  if (!myChart) return
  if (!searchQuery.value) {
    myChart.dispatchAction({ type: 'downplay', seriesIndex: 0 })
    return
  }
  
  // 查找匹配的节点
  const nodes = graphRawData.nodes
  const foundNode = nodes.find((n: any) => 
    n.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
  
  if (foundNode) {
    myChart.dispatchAction({
      type: 'focusNodeAdjacency',
      seriesIndex: 0,
      dataIndex: nodes.indexOf(foundNode)
    })
  }
}

const handleNodeJump = (id: string | number) => {
  const node = graphRawData.nodes.find((n: any) => n.id === String(id))
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
    level_value: node.level || 1, // 使用逻辑难度等级
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
    stats.value = res.data.stats
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
  
  const categories = data.categories || []
  const categoryPalette = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ef4444', '#84cc16', '#f97316']
  const categoryColorMap = new Map(
    categories.map((c: any, index: number) => [
      c.name,
      c.itemStyle?.color || categoryPalette[index % categoryPalette.length]
    ])
  )
  const chartCategories = categories.map((c: any, index: number) => ({
    ...c,
    itemStyle: {
      ...(c.itemStyle || {}),
      color: categoryColorMap.get(c.name) || categoryPalette[index % categoryPalette.length]
    }
  }))

  const nodes = data.nodes.map((n: any) => {
    let symbol = 'circle'
    if (n.status === 'mastered') symbol = 'diamond'
    else if (n.status === 'ready') symbol = 'roundRect'
    
    return {
      ...n,
      categoryName: n.category,
      category: categories.findIndex((c: any) => c.name === n.category),
      symbol: symbol,
      itemStyle: {
        ...(n.itemStyle || {}),
        color: categoryColorMap.get(n.category)
      }
    }
  })

  myChart = echarts.init(chartRef.value)
  const option = {
    backgroundColor: '#ffffff', // 强制背景色，提升对比度
    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#ebeef5',
      borderWidth: 1,
      padding: [10, 15],
      textStyle: { color: '#606266', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 8px;',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const statusMap: any = { mastered: '已掌握', ready: '可练习', locked: '未解锁' }
          const statusColor: any = { mastered: '#52c41a', ready: '#faad14', locked: '#999' }
          return `
            <div style="font-weight:bold;margin-bottom:4px;">${params.name}</div>
            <div style="font-size:12px;">部位: ${params.data.category_name || params.data.categoryName || params.data.category}</div>
            <div style="font-size:12px;">状态: <span style="color:${statusColor[params.data.status]}">${statusMap[params.data.status]}</span></div>
            <div style="font-size:11px;color:#888;margin-top:4px;">${params.data.gnn_insight}</div>
          `
        } else if (params.dataType === 'edge') {
          return `
            <div style="font-size:12px;">关系: <b>${params.data.relation_label || '关联'}</b></div>
            <div style="font-size:12px;margin-top:4px;">
              ${params.data.source_name} ➔ ${params.data.target_name}
            </div>
          `
        }
        return ''
      }
    },
    legend: {
      show: true,
      data: chartCategories.map((c: any) => c.name),
      orient: 'vertical',
      right: 30,
      top: 'center',
      padding: [15, 20],
      backgroundColor: 'rgba(255, 255, 255, 0.8)',
      borderColor: '#f2f2f2',
      borderWidth: 1,
      borderRadius: 10,
      textStyle: { color: '#666', fontSize: 13, fontWeight: 500 },
      icon: 'circle',
      selectedMode: 'multiple' // 允许点击过滤分类，提升探索体验
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: data.links.map((l: any) => ({
          ...l,
          source_name: nodes.find((n: any) => n.id === l.source)?.name,
          target_name: nodes.find((n: any) => n.id === l.target)?.name,
        })),
        categories: chartCategories,
        roam: true,
        selectedMode: 'single', // 单选节点
        nodeScaleRatio: 0.6, // 缩放比例
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 11,
          fontWeight: 500,
          color: '#34495e',
          distance: 10 // 增加文字与节点的距离
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [5, 10],
        force: {
          initLayout: 'circular',
          repulsion: 3500, // 再次大幅增加斥力，让动作点位分布更广
          edgeLength: [150, 400], // 连线也要拉开，适应斥力
          gravity: 0.015, // 进一步减小引力，允许图谱在中心点外更大范围扩展
          friction: 0.25, // 细微调整摩擦力
          layoutAnimation: true
        },
        draggable: true,
        emphasis: {
          focus: 'adjacency',
          lineStyle: { 
            width: 5,
            opacity: 1
          },
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        lineStyle: {
          curveness: 0.3, // 增加弧度，减少重叠
          opacity: 0.3,
          width: 2
        }
      }
    ]
  }

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
  router.push({ 
    path: '/exercises', 
    query: { actionId: id }
  })
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
  height: calc(100vh - 40px); /* 增加可用空间 */
  display: flex;
  flex-direction: column;
  background-color: #f8f9fa;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 15px 25px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.search-input {
  width: 250px;
}

.progress-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.stat-item {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.graph-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
  padding: 0 5px;
}

.status-legend {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.graph-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
  height: 0;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
  border: none;
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

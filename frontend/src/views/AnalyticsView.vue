<template>
    <div class="analytics-container" v-loading="loading">
        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="summary-card">
                    <template #header>
                        <div class="card-header">
                            <span>训练统计概览</span>
                            <div class="header-actions">
                                <el-radio-group v-model="timerange" size="small" @change="fetchData">
                                    <el-radio-button :label="7">最近一周</el-radio-button>
                                    <el-radio-button :label="30">最近一月</el-radio-button>
                                </el-radio-group>
                                <el-button size="small" :icon="Download" :disabled="!summary.daily_breakdown.length" @click="exportCsv">
                                    导出 CSV
                                </el-button>
                            </div>
                        </div>
                    </template>
                    <el-row :gutter="20">
                        <el-col :xs="24" :md="8">
                            <el-statistic title="总活跃时长" :value="summary.total_duration">
                                <template #suffix> 分钟</template>
                            </el-statistic>
                        </el-col>
                        <el-col :xs="24" :md="8">
                            <el-statistic title="累计消耗" :value="summary.total_calories" :precision="0">
                                <template #suffix> kcal</template>
                            </el-statistic>
                        </el-col>
                        <el-col :xs="24" :md="8">
                            <el-statistic title="平均动作评分" :value="summary.avg_form_score" :precision="1">
                                <template #suffix> / 100</template>
                            </el-statistic>
                        </el-col>
                    </el-row>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :xs="24" :md="16">
                <el-card class="chart-card">
                    <template #header>每日能量消耗 (kcal)</template>
                    <v-chart class="chart" :option="calorieOption" autoresize />
                </el-card>
            </el-col>
            <el-col :xs="24" :md="8">
                <el-card class="chart-card">
                    <template #header>动作质量分布</template>
                    <v-chart class="chart" :option="scoreOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :span="24">
                <el-card>
                    <template #header>
                        <div class="card-header">
                            <span>进步追踪 (动作详情)</span>
                            <span class="card-hint">共 {{ summary.daily_breakdown.length }} 天记录</span>
                        </div>
                    </template>
                    <el-empty v-if="!loading && !summary.daily_breakdown.length" description="还没有训练数据，完成一次训练后再来看看" />
                    <el-table v-else :data="summary.daily_breakdown" stripe :style="{ width: '100%' }">
                        <el-table-column prop="date" label="日期" width="120" />
                        <el-table-column prop="completed_sessions" label="完成会话" />
                        <el-table-column prop="total_duration_minutes" label="课时(分)" />
                        <el-table-column prop="total_calories_burned" label="消耗(kcal)">
                            <template #default="scope">
                                {{ scope.row.total_calories_burned.toFixed(0) }}
                            </template>
                        </el-table-column>
                        <el-table-column prop="average_form_score" label="AI 评分">
                            <template #default="scope">
                                <el-tag :type="scope.row.average_form_score > 80 ? 'success' : 'warning'">
                                    {{ scope.row.average_form_score.toFixed(1) }}
                                </el-tag>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'
import { useTheme } from '../composables/useTheme'

use([
    CanvasRenderer,
    BarChart,
    PieChart,
    LineChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent
])

const { resolved } = useTheme()
const timerange = ref(7)
const loading = ref(false)

const cssVar = (name: string, fallback: string) => {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    return value || fallback
}

const chartColors = () => ({
    surface: cssVar('--fv-surface', '#ffffff'),
    border: cssVar('--fv-border', 'rgba(16,24,40,0.09)'),
    text: cssVar('--fv-text', '#0f172a'),
    textSecondary: cssVar('--fv-text-2', '#64748b'),
    accent: cssVar('--fv-primary', '#c2410c'),
    accentSoft: cssVar('--fv-accent', '#65a30d'),
    accentDeep: cssVar('--fv-primary-strong', '#5546e8'),
})

const summary = reactive({
    total_calories: 0,
    total_duration: 0,
    avg_form_score: 0,
    daily_breakdown: [] as any[]
})

const calorieOption = ref<any>({
    tooltip: { trigger: 'axis' },
    grid: { left: 12, right: 18, top: 24, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: [], axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
        data: [],
        type: 'bar',
        barMaxWidth: 26,
        itemStyle: { borderRadius: [6, 6, 0, 0] }
    }]
})

const scoreOption = ref<any>({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 9, itemHeight: 9 },
    series: [
        {
            type: 'pie',
            radius: ['46%', '72%'],
            center: ['50%', '44%'],
            avoidLabelOverlap: true,
            label: { show: false },
            data: []
        }
    ]
})

const applyChartTheme = () => {
    const colors = chartColors()
    const tooltip = {
        backgroundColor: colors.surface,
        borderColor: colors.border,
        borderWidth: 1,
        textStyle: { color: colors.text },
    }

    calorieOption.value.tooltip = { trigger: 'axis', ...tooltip }
    calorieOption.value.xAxis.axisLabel = { color: colors.textSecondary }
    calorieOption.value.yAxis.axisLabel = { color: colors.textSecondary }
    calorieOption.value.yAxis.splitLine.lineStyle.color = colors.border
    calorieOption.value.series[0].itemStyle = {
        color: colors.accent,
        borderRadius: [6, 6, 0, 0],
    }

    scoreOption.value.tooltip = { trigger: 'item', ...tooltip }
    scoreOption.value.legend.textStyle = { color: colors.textSecondary }
    scoreOption.value.series[0].color = [colors.accentDeep, colors.accent, colors.accentSoft]
}

const fetchData = async () => {
    loading.value = true
    try {
        const res = await apiClient.get(`analytics/daily-stats/summary/?days=${timerange.value}`)
        const data = res.data
        summary.total_calories = data.total_calories
        summary.total_duration = data.total_duration
        summary.avg_form_score = data.avg_form_score
        summary.daily_breakdown = data.daily_breakdown

        calorieOption.value.xAxis.data = data.daily_breakdown.map((i: any) => i.date).reverse()
        calorieOption.value.series[0].data = data.daily_breakdown.map((i: any) => i.total_calories_burned).reverse()

        const scores = data.daily_breakdown.map((i: any) => i.average_form_score)
        scoreOption.value.series[0].data = [
            { value: scores.filter((s: number) => s >= 85).length, name: '优秀' },
            { value: scores.filter((s: number) => s >= 60 && s < 85).length, name: '合格' },
            { value: scores.filter((s: number) => s < 60).length, name: '待改进' }
        ]
        applyChartTheme()
    } catch (err) {
        console.error('Fetch analytics fail', err)
        ElMessage.error('统计数据加载失败，请稍后重试')
    } finally {
        loading.value = false
    }
}

const csvCell = (value: unknown) => `"${String(value ?? '').replace(/"/g, '""')}"`

const exportCsv = () => {
    if (!summary.daily_breakdown.length) return
    const header = ['日期', '完成会话', '训练时长(分钟)', '消耗(kcal)', 'AI 评分']
    const rows = summary.daily_breakdown.map((item: any) => [
        item.date,
        item.completed_sessions,
        item.total_duration_minutes,
        Number(item.total_calories_burned || 0).toFixed(0),
        Number(item.average_form_score || 0).toFixed(1),
    ])
    const csv = '\uFEFF' + [header, ...rows]
        .map((row) => row.map(csvCell).join(','))
        .join('\r\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `fitvision-analytics-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${rows.length} 天训练数据`)
}

watch(resolved, applyChartTheme)

onMounted(() => {
    applyChartTheme()
    fetchData()
})
</script>

<style scoped>
.analytics-container {
    background: transparent;
    color: var(--milan-text-primary);
    padding: 4px 0 24px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    color: var(--milan-text-primary);
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.card-hint {
    font-size: 12.5px;
    font-weight: 400;
    color: var(--milan-text-secondary);
}

.chart {
    height: 300px;
}

.chart-card {
    height: 400px;
}

.analytics-container :deep(.el-card) {
    border-radius: var(--fv-radius-md);
    border: 1px solid var(--milan-bg-surface);
    box-shadow: var(--fv-shadow-sm);
}

.analytics-container :deep(.el-card__header) {
    color: var(--milan-text-primary);
    font-weight: 700;
}

.analytics-container :deep(.el-statistic__head) {
    color: var(--milan-text-secondary);
}

.analytics-container :deep(.el-statistic__content) {
    color: var(--milan-text-primary);
}

.analytics-container :deep(.el-table) {
    --el-table-border-color: var(--milan-bg-surface);
    --el-table-header-bg-color: var(--milan-on-accent);
    --el-table-row-hover-bg-color: var(--milan-bg-hover);
    --el-table-text-color: var(--milan-text-primary);
    --el-table-header-text-color: var(--milan-text-secondary);
}

@media (max-width: 768px) {
    .analytics-container {
        padding: 0 0 16px;
    }
    .card-header {
        flex-direction: column;
        align-items: flex-start;
    }
    .header-actions {
        width: 100%;
        justify-content: space-between;
    }
    .chart-card {
        height: 340px;
    }
    .chart {
        height: 240px;
    }
}
</style>

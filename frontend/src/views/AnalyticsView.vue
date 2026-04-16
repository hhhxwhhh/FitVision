<template>
    <div class="analytics-container">
        <el-row :gutter="20">
            <el-col :span="24">
                <el-card class="summary-card">
                    <template #header>
                        <div class="card-header">
                            <span>📊 训练统计概览</span>
                            <el-radio-group v-model="timerange" size="small" @change="fetchData">
                                <el-radio-button :label="7">最近一周</el-radio-button>
                                <el-radio-button :label="30">最近一月</el-radio-button>
                            </el-radio-group>
                        </div>
                    </template>
                    <el-row :gutter="20">
                        <el-col :span="8">
                            <el-statistic title="总活跃时长" :value="summary.total_duration">
                                <template #suffix> 分钟</template>
                            </el-statistic>
                        </el-col>
                        <el-col :span="8">
                            <el-statistic title="累计消耗" :value="summary.total_calories" :precision="0">
                                <template #suffix> kcal</template>
                            </el-statistic>
                        </el-col>
                        <el-col :span="8">
                            <el-statistic title="平均动作评分" :value="summary.avg_form_score" :precision="1">
                                <template #suffix> / 100</template>
                            </el-statistic>
                        </el-col>
                    </el-row>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :span="16">
                <el-card class="chart-card">
                    <template #header>每日能量消耗 (kcal)</template>
                    <v-chart class="chart" :option="calorieOption" autoresize />
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card class="chart-card">
                    <template #header>动作质量分布</template>
                    <v-chart class="chart" :option="scoreOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;">
            <el-col :span="24">
                <el-card>
                    <template #header>进步追踪 (动作详情)</template>
                    <el-table :data="summary.daily_breakdown" stripe style="width: 100%">
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
import { ref, onMounted, reactive } from 'vue'
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
import apiClient from '../api'

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

const timerange = ref(7)

// 米兰色系（当前页面专用）
const MILAN_COLORS = {
    pageBase: '#F5F2ED', // 页面背景 / 卡片底色
    surface: '#E5E0D8', // 卡片边框 / 分隔线
    textPrimary: '#3C2F2F', // 主标题 / 正文
    textSecondary: '#7D756D', // 次级文字 / 注释
    accent: '#BEA47E', // 主图表色 / 选中态
    accentSoft: '#D5C6B0', // 次级图表色
    accentDeep: '#9F8462', // 深强调图表色
}

const summary = reactive({
    total_calories: 0,
    total_duration: 0,
    avg_form_score: 0,
    daily_breakdown: [] as any[]
})

const calorieOption = ref<any>({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value' },
    series: [{
        data: [],
        type: 'bar',
        itemStyle: { color: MILAN_COLORS.accent }
    }]
})

const scoreOption = ref<any>({
    tooltip: { trigger: 'item' },
    series: [
        {
            type: 'pie',
            radius: ['40%', '70%'],
            color: [MILAN_COLORS.accentDeep, MILAN_COLORS.accent, MILAN_COLORS.accentSoft],
            data: []
        }
    ]
})

const fetchData = async () => {
    try {
        const res = await apiClient.get(`analytics/daily-stats/summary/?days=${timerange.value}`)
        const data = res.data
        summary.total_calories = data.total_calories
        summary.total_duration = data.total_duration
        summary.avg_form_score = data.avg_form_score
        summary.daily_breakdown = data.daily_breakdown

        // 更新图表
        calorieOption.value.xAxis.data = data.daily_breakdown.map((i: any) => i.date).reverse()
        calorieOption.value.series[0].data = data.daily_breakdown.map((i: any) => i.total_calories_burned).reverse()

        // 评分简单分类
        const scores = data.daily_breakdown.map((i: any) => i.average_form_score)
        scoreOption.value.series[0].data = [
            { value: scores.filter((s: number) => s >= 85).length, name: '优秀' },
            { value: scores.filter((s: number) => s >= 60 && s < 85).length, name: '合格' },
            { value: scores.filter((s: number) => s < 60).length, name: '待改进' }
        ]
    } catch (err) {
        console.error('Fetch analytics fail', err)
    }
}

onMounted(() => {
    fetchData()
})
</script>

<style scoped>
.analytics-container {
    --milan-bg-main: #F5F2ED; /* 页面大背景 / 内容背景 */
    --milan-bg-surface: #E5E0D8; /* 卡片边框 / 表格分隔 */
    --milan-bg-hover: #EFE8DD; /* 表格悬浮态背景 */
    --milan-text-primary: #3C2F2F; /* 主标题 / 主文本 */
    --milan-text-secondary: #7D756D; /* 辅助说明文字 */
    --milan-accent: #BEA47E; /* 交互强调 / 图表主色 */
    --milan-shadow-soft: rgba(60, 47, 47, 0.08); /* 浮层阴影 */

    background: var(--milan-bg-main);
    color: var(--milan-text-primary);
    padding: 20px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--milan-text-primary);
}

.chart {
    height: 300px;
}

.chart-card {
    height: 400px;
}

.analytics-container :deep(.el-card) {
    background: var(--milan-bg-main);
    border: 1px solid var(--milan-bg-surface);
    box-shadow: 0 4px 10px var(--milan-shadow-soft);
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

.analytics-container :deep(.el-radio-button__inner) {
    color: var(--milan-text-secondary);
    border-color: var(--milan-bg-surface);
    background: var(--milan-bg-main);
}

.analytics-container :deep(.el-radio-button__orig-radio:checked + .el-radio-button__inner) {
    background: var(--milan-accent);
    border-color: var(--milan-accent);
    box-shadow: -1px 0 0 0 var(--milan-accent);
    color: var(--milan-bg-main);
}

.analytics-container :deep(.el-table) {
    --el-table-border-color: var(--milan-bg-surface);
    --el-table-header-bg-color: var(--milan-bg-main);
    --el-table-row-hover-bg-color: var(--milan-bg-hover);
    --el-table-text-color: var(--milan-text-primary);
    --el-table-header-text-color: var(--milan-text-secondary);
}
</style>

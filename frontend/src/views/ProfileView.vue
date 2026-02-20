<template>
  <div class="page-container">
    <div class="profile-hero">
      <div class="hero-left">
        <div class="avatar-upload-container">
          <el-avatar :size="80" :src="form.avatar" :icon="UserFilled" class="hero-avatar" />
          <div class="avatar-overlay" @click="triggerUpload">
            <el-icon><Edit /></el-icon>
          </div>
          <input type="file" ref="fileInput" class="hidden-input" accept="image/*" @change="handleFileChange" />
        </div>
        <div class="hero-info">
          <h1 class="username-display">{{ form.nickname || '未设置昵称' }}</h1>
          <p class="account-id">ID: {{ form.username }}</p>
          <div class="account-badges">
             <el-tag size="small" effect="light" round>
               <el-icon><Calendar /></el-icon> 活跃 {{ stats.total_training_days }} 天
             </el-tag>
             <el-tag size="small" type="success" effect="light" round>
               <el-icon><Medal /></el-icon> 经验评分: {{ stats.best_accuracy_score.toFixed(0) }}
             </el-tag>
          </div>
        </div>
      </div>
      <div class="hero-right">
        <el-button @click="handleLogout" class="logout-btn">
          退出登录
        </el-button>
        <el-button type="primary" size="large" @click="handleSave" :loading="loading" :disabled="!isFormChanged" class="save-btn shadow-btn">
          保存修改
        </el-button>
      </div>
    </div>

    <!-- Stats Dashboard Section -->
    <div class="stats-grid">
       <div class="stat-card">
          <div class="stat-icon purple"><el-icon><Timer /></el-icon></div>
          <div class="stat-content">
             <span class="stat-label">累计训练</span>
             <div class="stat-value-box">
                <span class="stat-value">{{ stats.total_training_time }}</span>
                <span class="stat-unit">分钟</span>
             </div>
          </div>
       </div>
       <div class="stat-card">
          <div class="stat-icon orange"><el-icon><Chicken /></el-icon></div>
          <div class="stat-content">
             <span class="stat-label">热量消耗</span>
             <div class="stat-value-box">
                <span class="stat-value">{{ stats.total_calories_burned.toFixed(0) }}</span>
                <span class="stat-unit">kcal</span>
             </div>
          </div>
       </div>
       <div class="stat-card">
          <div class="stat-icon blue"><el-icon><TrendCharts /></el-icon></div>
          <div class="stat-content">
             <span class="stat-label">完成动作</span>
             <div class="stat-value-box">
                <span class="stat-value">{{ stats.total_trainings }}</span>
                <span class="stat-unit">次</span>
             </div>
          </div>
       </div>
    </div>

    <!-- Activity Heatmap Section -->
    <el-card class="heatmap-card mb-6" shadow="never">
       <div class="card-title-bar">
          <div class="title-with-extra">
             <h3>📊 训练热力图</h3>
             <div class="heatmap-legend">
                <span>较少</span>
                <div class="legend-scale">
                   <div class="scale-item level-0"></div>
                   <div class="scale-item level-1"></div>
                   <div class="scale-item level-2"></div>
                   <div class="scale-item level-3"></div>
                   <div class="scale-item level-4"></div>
                </div>
                <span>较多</span>
             </div>
          </div>
          <small>每一份努力都将被记录，加油！</small>
       </div>
       <div class="heatmap-container" v-loading="heatmapLoading">
          <v-chart class="chart-heatmap" :option="heatmapOption" autoresize />
       </div>
    </el-card>

    <el-row :gutter="24">
      <el-col :md="24" :lg="16" class="col-left">
        <el-card class="profile-card">
          <!-- Form Header -->
          <div class="card-title-bar">
             <h3>📝 资料设置</h3>
             <small>完善资料库，AI 将为您推荐更准确的运动负荷</small>
          </div>

          <el-form label-position="top" :model="form" :rules="rules" ref="formRef" class="profile-form">
            <div class="form-section-header">基本概况</div>
            <el-row :gutter="24">
              <el-col :md="12">
                <el-form-item label="昵称" prop="nickname">
                  <el-input v-model="form.nickname" placeholder="给自己起个名字" maxlength="50" size="large">
                     <template #prefix>
                        <el-icon><User /></el-icon>
                     </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :md="12">
                <el-form-item label="电子邮箱">
                  <el-input v-model="form.email" placeholder="绑定邮箱接收报表" size="large" disabled>
                     <template #prefix>
                        <el-icon><Message /></el-icon>
                     </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
               <el-col :md="8">
                <el-form-item label="性别" prop="gender">
                  <el-select v-model="form.gender" size="large" style="width: 100%">
                    <el-option label="男" value="male" />
                    <el-option label="女" value="female" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :md="8">
                 <el-form-item label="年龄" prop="age">
                  <el-input-number v-model="form.age" :min="1" :max="120" style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="身高 (cm)" prop="height">
                  <el-input-number v-model="form.height" :min="100" :max="250" :precision="1" controls-position="right"
                    style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="当前体重 (kg)" prop="weight">
                  <el-input-number v-model="form.weight" :min="30" :max="200" :precision="1" controls-position="right"
                    style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="form-section-header">运动状态</div>
            <el-row :gutter="24">
              <el-col :md="12">
                <el-form-item label="目标体重 (kg)">
                  <el-input-number v-model="form.target_weight" :min="30" :max="200" :precision="1" controls-position="right"
                    style="width: 100%" size="large" />
                </el-form-item>
              </el-col>
              <el-col :md="12">
                <el-form-item label="日常活动水平">
                  <el-select v-model="form.activity_level" size="large" style="width: 100%">
                    <el-option v-for="(val, key) in activityLevelMap" :key="key" :label="val.label" :value="key">
                      <div class="select-option-content">
                        <span>{{ val.label }}</span>
                        <small class="option-desc">{{ val.desc }}</small>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="训练经验">
              <el-radio-group v-model="form.fitness_level" size="large" class="level-radio-group">
                <el-radio-button label="beginner">
                    <div class="radio-btn-content">新手<span>小白</span></div>
                </el-radio-button>
                <el-radio-button label="intermediate">
                    <div class="radio-btn-content">进阶<span>有基础</span></div>
                </el-radio-button>
                <el-radio-button label="advanced">
                    <div class="radio-btn-content">大神<span>核心玩家</span></div>
                </el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="身体伤病历史">
               <el-input v-model="form.injury_history" type="textarea" 
                    placeholder="若有腰痛、膝盖损伤等请务必告知。如无则填写‘无’。AI 将避开可能加重损伤的动作。"
                    :autosize="{ minRows: 3, maxRows: 5 }" 
                    class="styled-textarea"
                />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :md="24" :lg="8" class="col-right">
        <!-- AI 能力分析雷达图 -->
        <el-card class="radar-card mb-4" shadow="never">
          <div class="card-title-bar slim">
             <h3>🧠 能力评估</h3>
             <small>AI 根据历史表现分析你的体能偏向</small>
          </div>
          <div class="radar-container">
             <v-chart class="chart-radar" :option="radarOption" autoresize />
          </div>
        </el-card>

        <!-- Body Metrics Card -->
        <el-card class="metrics-card">
          <div class="metrics-header">
             <div>
                <h3>身体指标解析</h3>
                <span class="last-update" v-if="form.updated_at">上次更新: {{ formatDate(form.updated_at) }}</span>
             </div>
             <el-tag effect="plain" round>AI Calculated</el-tag>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">BMI 体质指数</div>
            <div class="metric-value-row">
               <div class="metric-value">{{ computedBMI.toFixed(1) }}</div>
               <el-tag :type="getBMIType(computedBMI)" effect="dark" round>
                  {{ getBMIText(computedBMI) }}
               </el-tag>
            </div>
            <el-progress :percentage="Math.min(computedBMI * 2.5, 100)" :color="getBMIColor(computedBMI)" :show-text="false" :stroke-width="8" class="mt-2" />
          </div>

          <div class="metric-divider"></div>

          <div class="metric-item">
             <div class="metric-label">BMR 基础代谢 (维持生命所需)</div>
             <div class="metric-value-row">
                <div class="metric-value">{{ Math.round(computedBMR) }} <span class="unit">kcal</span></div>
             </div>
          </div>

          <div class="metric-item highlight-metric">
             <div class="metric-label">TDEE 每日总热量消耗 (目标摄入参考)</div>
             <div class="metric-value-row">
                <div class="metric-value colored">{{ Math.round(computedTDEE) }} <span class="unit">kcal</span></div>
                <div class="trend-indicator up">
                    <span v-if="form.activity_level !== 'sedentary'">🔥 燃脂效率高</span>
                </div>
             </div>
             <p class="metric-desc">根据您的活动量算出的全天总支出。如果您想减重，摄入量应略低于此数值。</p>
          </div>

          <div class="metric-divider"></div>

          <div class="info-section">
             <div class="data-badge-list">
                 <div class="data-badge">
                     <span class="badge-icon">🎯</span>
                     <span class="badge-text">体重差: {{ (form.weight - form.target_weight).toFixed(1) }}kg</span>
                 </div>
                 <div class="data-badge">
                     <span class="badge-icon">⚡</span>
                     <span class="badge-text">活跃系数: {{ activityLevelMap[form.activity_level as keyof typeof activityLevelMap]?.factor }}</span>
                 </div>
             </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import { 
  User, UserFilled, Calendar, Medal, Timer, Chicken, 
  TrendCharts, Message, Location, Promotion, Edit, Delete
} from '@element-plus/icons-vue'
import type { FormInstance } from 'element-plus'
import dayjs from 'dayjs'
import apiClient from '@/api'

const router = useRouter()
const userStore = useUserStore()

// ECharts for Heatmap
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart, ScatterChart, RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CalendarComponent,
  GridComponent,
  LegendComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  HeatmapChart,
  ScatterChart,
  RadarChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CalendarComponent,
  GridComponent,
  LegendComponent
])

const loading = ref(false)
const heatmapLoading = ref(false)
const formRef = ref<FormInstance>()
const fileInput = ref<HTMLInputElement>()
const avatarFile = ref<File | null>(null)
const isFormChanged = ref(false)
const stats = reactive({
  total_trainings: 0,
  total_training_days: 0,
  total_training_time: 0,
  total_calories_burned: 0,
  best_accuracy_score: 0,
})

const heatmapData = ref<any[]>([])

const heatmapOption = computed(() => {
  const currentYear = new Date().getFullYear()
  return {
    tooltip: {
      position: 'top',
      formatter: (p: any) => {
        const val = p.data[1]
        return `${p.data[0]}: ${val > 0 ? `训练消耗 ${val.toFixed(0)} kcal` : '休息日'}`
      }
    },
    visualMap: {
      min: 0,
      max: 500,
      type: 'piecewise',
      orient: 'horizontal',
      left: 'center',
      top: 0,
      show: false,
      pieces: [
        { min: 0, max: 0, color: '#ebedf0' },
        { min: 1, max: 150, color: '#c6e48b' },
        { min: 151, max: 300, color: '#7bc96f' },
        { min: 301, max: 450, color: '#239a3b' },
        { min: 451, color: '#196127' }
      ]
    },
    calendar: {
      top: 30,
      left: 30,
      right: 30,
      cellSize: ['auto', 13],
      range: currentYear,
      itemStyle: {
        borderWidth: 0.5,
        borderColor: '#fff'
      },
      yearLabel: { show: false },
      dayLabel: { firstDay: 1, nameMap: 'cn', color: '#94a3b8', fontSize: 10 },
      monthLabel: { nameMap: 'cn', color: '#94a3b8', fontSize: 10 }
    },
    series: {
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: heatmapData.value
    }
  }
})

const radarOption = computed(() => {
  return {
    radar: {
      indicator: [
        { name: '力量', max: 5000 },
        { name: '耐力', max: 5000 },
        { name: '精准', max: 100 },
        { name: '频率', max: 100 },
        { name: '表现', max: 100 }
      ],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#94a3b8',
        fontSize: 10
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.1)'
        }
      },
      splitArea: {
        show: false
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.1)'
        }
      }
    },
    series: [
      {
        name: '能力概览',
        type: 'radar',
        data: [
          {
            value: [
               stats.total_calories_burned || 0,
               stats.total_training_time || 0,
               stats.best_accuracy_score || 0,
               stats.total_trainings || 0,
               stats.total_training_days || 0
            ],
            name: '当前表现',
            symbol: 'none',
            itemStyle: {
              color: '#3b82f6'
            },
            areaStyle: {
              color: 'rgba(59, 130, 246, 0.2)'
            },
            lineStyle: {
                width: 2,
                color: '#3b82f6'
            }
          }
        ]
      }
    ]
  }
})

const formatDate = (date: string) => {
    return date ? dayjs(date).format('YYYY-MM-DD HH:mm') : ''
}

const form = reactive({
  username: '',
  email: '',
  avatar: '',
  nickname: '',
  gender: 'male' as 'male' | 'female',
  age: 25,
  height: 170,
  weight: 65,
  fitness_level: 'beginner',
  injury_history: '',
  activity_level: 'moderate',
  target_weight: 60,
  updated_at: ''
})

const rules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  age: [{ required: true, message: '请输入年龄', trigger: 'blur' }],
  height: [{ required: true, message: '请输入身高', trigger: 'blur' }],
  weight: [{ required: true, message: '请输入体重', trigger: 'blur' }],
}

const activityLevelMap = {
  sedentary: { label: '久坐不动', factor: 1.2, desc: '办公室工作，极少运动' },
  light: { label: '轻度活动', factor: 1.375, desc: '每周运动 1-3 天' },
  moderate: { label: '中度活动', factor: 1.55, desc: '每周运动 3-5 天' },
  active: { label: '高度活动', factor: 1.725, desc: '每周运动 6-7 天' },
  very_active: { label: '极高活动', factor: 1.9, desc: '专业运动员或高体力活' }
}

let originalFormStr = ''

const computedBMI = computed(() => {
  if (!form.height || !form.weight) return 0
  return form.weight / ((form.height / 100) * (form.height / 100))
})

const computedBMR = computed(() => {
  if (!form.weight || !form.height || !form.age) return 0
  if (form.gender === 'male') {
    return 10 * form.weight + 6.25 * form.height - 5 * form.age + 5
  } else {
    return 10 * form.weight + 6.25 * form.height - 5 * form.age - 161
  }
})

const computedTDEE = computed(() => {
  const level = form.activity_level as keyof typeof activityLevelMap
  const factor = activityLevelMap[level]?.factor || 1.2
  return computedBMR.value * factor
})

const getBMIType = (bmi: number) => {
  if (bmi < 18.5) return 'warning'
  if (bmi < 24) return 'success'
  if (bmi < 28) return 'warning'
  return 'danger'
}

const getBMIColor = (bmi: number) => {
  if (bmi < 18.5) return '#e6a23c'
  if (bmi < 24) return '#67c23a'
  if (bmi < 28) return '#e6a23c'
  return '#f56c6c'
}

const getBMIText = (bmi: number) => {
  if (bmi < 18.5) return '偏瘦'
  if (bmi < 24) return '正常'
  if (bmi < 28) return '超重'
  return '肥胖'
}

watch(form, () => {
  isFormChanged.value = JSON.stringify(form) !== originalFormStr || !!avatarFile.value
}, { deep: true })

onMounted(async () => {
  loading.value = true
  heatmapLoading.value = true
  try {
    const [profileRes, statsRes, heatmapRes] = await Promise.all([
      apiClient.get('auth/profile/'),
      apiClient.get('auth/stats/'),
      apiClient.get('analytics/daily-stats/summary/?days=365')
    ])
    Object.assign(form, profileRes.data)
    Object.assign(stats, statsRes.data)
    
    // Prepare heatmap data
    if (heatmapRes.data?.daily_breakdown) {
      heatmapData.value = heatmapRes.data.daily_breakdown.map((i: any) => [
        i.date, 
        i.total_calories_burned || 0
      ])
    }
    
    originalFormStr = JSON.stringify(form)
    isFormChanged.value = false
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '无法获取个人资料')
  } finally {
    loading.value = false
    heatmapLoading.value = false
  }
})

const triggerUpload = () => {
    fileInput.value?.click()
}

const handleFileChange = (e: Event) => {
    const target = e.target as HTMLInputElement
    if (target.files && target.files[0]) {
        const file = target.files[0]
        avatarFile.value = file
        // Preview
        const reader = new FileReader()
        reader.onload = (re) => {
            form.avatar = re.target?.result as string
        }
        reader.readAsDataURL(file)
    }
}

const handleSave = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const formData = new FormData()
      
      // 只发送需要更新的字段，过滤掉只读字段和无效的 null 值
      const updateFields = [
        'nickname', 'gender', 'age', 'height', 'weight', 
        'fitness_level', 'injury_history', 'activity_level', 
        'target_weight', 'email'
      ]
      
      updateFields.forEach(key => {
          const val = (form as any)[key]
          if (val !== undefined && val !== null && val !== '') {
              formData.append(key, val)
          }
      })
      
      // Avatar file specifically
      if (avatarFile.value) {
          formData.append('avatar', avatarFile.value)
      }

      const res = await apiClient.put('auth/profile/', formData, {
          headers: {
              'Content-Type': 'multipart/form-data'
          }
      })
      
      Object.assign(form, res.data)
      originalFormStr = JSON.stringify(form)
      avatarFile.value = null
      isFormChanged.value = false
      
      // 更新全局 store，使 Header 的头像和昵称立即更新
      await userStore.fetchUser()
      
      ElMessage.success('保存成功！AI 已更新你的身体参数')
    } catch (err: any) {
        const errorData = err.response?.data
        console.error('Save profile failed:', errorData || err)
        let errorMsg = '保存失败，请检查网络或参数'
        if (errorData && typeof errorData === 'object') {
            errorMsg = Object.entries(errorData)
                .map(([key, value]) => {
                    const msg = Array.isArray(value) ? value.join(', ') : value
                    return `${key}: ${msg}`
                })
                .join('; ')
        }
        ElMessage.error({
            message: `保存失败: ${errorMsg}`,
            duration: 5000,
            showClose: true
        })
    } finally {
      loading.value = false
    }
  })
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }).catch(() => {})
}
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 60px;
}

/* Hero Section */
.profile-hero {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    padding: 32px;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    margin-bottom: 24px;
}

.hero-left {
    display: flex;
    align-items: center;
    gap: 24px;
}

.avatar-upload-container {
    position: relative;
    cursor: pointer;
    border-radius: 50%;
    overflow: hidden;
    width: 80px;
    height: 80px;
}

.avatar-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 20px;
    opacity: 0;
    transition: opacity 0.3s;
}

.avatar-upload-container:hover .avatar-overlay {
    opacity: 1;
}

.hidden-input {
    display: none;
}

.hero-avatar {
    background-color: #f1f5f9;
    color: #64748b;
    border: 4px solid #fff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.username-display {
    margin: 0;
    font-size: 28px;
    font-weight: 700;
    color: #1e293b;
}

.account-id {
    margin: 4px 0 12px;
    font-size: 14px;
    color: #94a3b8;
}

.account-badges {
    display: flex;
    gap: 12px;
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.03);
    transition: transform 0.2s;
}

.stat-card:hover {
    transform: translateY(-4px);
}

.stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
}

.stat-icon.purple { background: #f3e8ff; color: #a855f7; }
.stat-icon.orange { background: #ffedd5; color: #f97316; }
.stat-icon.blue { background: #e0f2fe; color: #0ea5e9; }

.stat-content {
    display: flex;
    flex-direction: column;
}

.stat-label {
    font-size: 13px;
    color: #94a3b8;
}

.stat-value-box {
    display: flex;
    align-items: baseline;
    gap: 4px;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
}

.stat-unit {
    font-size: 12px;
    color: #94a3b8;
}

.profile-card {
  border-radius: 20px;
  border: none;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.card-title-bar {
    padding-bottom: 24px;
    border-bottom: 1px solid #f1f5f9;
    margin-bottom: 24px;
}

.card-title-bar h3 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #1e293b;
}

.card-title-bar small {
    color: #94a3b8;
    font-size: 13px;
}

.profile-form :deep(.el-form-item__label) {
    font-weight: 500;
    font-size: 15px;
    color: var(--text-regular);
}

.form-section-header {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-color-primary);
    margin: 24px 0 16px;
    padding-left: 12px;
    border-left: 4px solid var(--el-color-primary);
    background: rgba(var(--el-color-primary-rgb), 0.05);
    line-height: 2;
}

.form-section-header:first-child {
    margin-top: 0;
}

.select-option-content {
    display: flex;
    flex-direction: column;
    padding: 4px 0;
}

.option-desc {
    font-size: 12px;
    color: #909399;
    line-height: 1.2;
}

.level-radio-group {
    display: flex;
    width: 100%;
}

.level-radio-group :deep(.el-radio-button) {
    flex: 1;
}

.level-radio-group :deep(.el-radio-button__inner) {
    width: 100%;
    height: 100%;
    padding: 12px 0;
    border-radius: 0;
}

.level-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
    border-radius: 8px 0 0 8px;
}

.level-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
    border-radius: 0 8px 8px 0;
}

.radio-btn-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    line-height: 1.2;
}

.hero-right {
    display: flex;
    gap: 16px;
    align-items: center;
}

.logout-btn {
    border: 1px solid #e2e8f0;
    color: #64748b;
    font-weight: 500;
}

.logout-btn:hover {
    background-color: #fef2f2;
    color: #ef4444;
    border-color: #fee2e2;
}

.save-btn {
    font-weight: 600;
}

.shadow-btn {
    box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.4);
}

/* Right Col Metrics */
.metrics-card {
   background: white; 
   color: #1e293b;
   border: none;
   border-radius: 20px;
   position: sticky;
   top: 24px;
   box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.metrics-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}

.metrics-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #1e293b;
}

.last-update {
    font-size: 11px;
    color: #94a3b8;
    display: block;
    margin-top: 4px;
}

.metric-item {
    margin-bottom: 20px;
}

.highlight-metric {
    background: #f8fafc;
    padding: 16px;
    border-radius: 12px;
    border-left: 4px solid #60a5fa;
}

.metric-label {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 8px;
    display: block;
}

.metric-value-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #1e293b;
    line-height: 1;
}

.metric-value.colored {
    color: #3b82f6;
}

.metric-value .unit {
    font-size: 14px;
    color: #94a3b8;
    font-weight: 400;
    margin-left: 4px;
}

.trend-indicator {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #f0fdf4;
    color: #16a34a;
}

.metric-desc {
    font-size: 12px;
    color: #64748b;
    margin-top: 10px;
    line-height: 1.6;
}

.metric-divider {
    height: 1px;
    background: #f1f5f9;
    margin: 20px 0;
}

.data-badge-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.data-badge {
    background: #f1f5f9;
    padding: 8px 12px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.badge-text {
    font-size: 13px;
    color: #475569;
}

.mt-2 {
    margin-top: 12px;
}

.mb-6 {
    margin-bottom: 24px;
}

/* Heatmap Section */
.heatmap-card {
    border-radius: 20px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    background: white;
}

.heatmap-card :deep(.el-card__body) {
    padding: 24px;
}

.title-with-extra {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.heatmap-legend {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #94a3b8;
}

.legend-scale {
    display: flex;
    gap: 3px;
}

.scale-item {
    width: 10px;
    height: 10px;
    border-radius: 2px;
}

.scale-item.level-0 { background: #ebedf0; }
.scale-item.level-1 { background: #c6e48b; }
.scale-item.level-2 { background: #7bc96f; }
.scale-item.level-3 { background: #239a3b; }
.scale-item.level-4 { background: #196127; }

.heatmap-container {
    height: 200px;
    width: 100%;
}

.chart-heatmap {
    height: 100%;
    width: 100%;
}

.mb-4 {
    margin-bottom: 32px;
}

/* Radar Section */
.radar-card {
    border-radius: 20px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.radar-card :deep(.el-card__body) {
    padding: 20px;
}

.card-title-bar.slim {
    padding-bottom: 12px;
}

.radar-container {
    height: 250px;
    width: 100%;
}

.chart-radar {
    height: 100%;
    width: 100%;
}

.col-right {
    margin-top: 24px;
}

.styled-textarea :deep(.el-textarea__inner) {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 12px;
    font-size: 14px;
    line-height: 1.6;
}

.styled-textarea :deep(.el-textarea__inner:focus) {
    background-color: white;
}

@media (min-width: 992px) {
    .col-right {
        margin-top: 0;
    }
}
</style>
<template>
  <div class="health-status">
    <el-tag :type="statusType" effect="dark" class="status-tag">
      <ProductIcon v-if="loading" name="spinner" :spinning="true" class="status-icon" />
      <ProductIcon v-else-if="statusType === 'success'" name="health-ok" class="status-icon" />
      <ProductIcon v-else-if="statusType === 'danger'" name="health-error" class="status-icon" />
      <ProductIcon v-else name="health-idle" class="status-icon" />
      <span class="status-text" data-testid="health-status-text">{{ statusText }}</span>
    </el-tag>

    <el-tooltip content="刷新状态" placement="bottom">
      <el-button
        type="primary"
        :loading="loading"
        :disabled="loading"
        class="refresh-button"
        @click="handleRefreshClick"
      >
        <ProductIcon v-if="!loading" name="refresh" class="control-icon" />
      </el-button>
    </el-tooltip>

    <el-popover placement="bottom" :width="320" trigger="hover">
      <template #reference>
        <ProductIcon name="info" class="info-icon" />
      </template>
      <div class="health-details">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="服务状态">
            <el-tag :type="healthData?.status === 'healthy' ? 'success' : 'danger'" size="small">
              {{ healthData?.status || '未知' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="引擎类型">
            {{ healthData?.engine || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="模型状态">
            <el-tag :type="healthData?.model_loaded ? 'success' : 'warning'" size="small">
              {{ healthData?.model_loaded ? '已加载' : '未加载' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="API 版本">
            {{ healthData?.version || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="最后检查">
            {{ lastCheckTime || '从未' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 错误信息 -->
        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          :closable="false"
          class="error-alert"
        />

        <!-- 重试信息 -->
        <div v-if="retryCount > 0 && !healthData" class="retry-info">
          <el-text type="warning" size="small">
            正在重试连接... ({{ retryCount }}/{{ maxRetries }})
          </el-text>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElPopover,
  ElTag,
  ElText,
  ElTooltip
} from 'element-plus'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import ProductIcon from '@/components/ProductIcon.vue'
import { apiService, ApiError } from '@/services/api'
import type { HealthResponse } from '@/types/api'

// 状态
const healthData = ref<HealthResponse | null>(null)
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const lastCheckTime = ref<string | null>(null)
const retryCount = ref(0)

// 配置
const maxRetries = 3
const retryDelay = 3000 // 3秒重试间隔
const autoRefreshInterval = 30000 // 30秒自动刷新

// 定时器
let retryTimer: number | null = null
let autoRefreshTimer: number | null = null

// 计算属性
const statusType = computed(() => {
  if (loading.value) return 'info'
  if (!healthData.value) return 'danger'
  if (healthData.value.status === 'healthy' && healthData.value.model_loaded) {
    return 'success'
  }
  if (healthData.value.status === 'healthy') {
    return 'warning'
  }
  return 'danger'
})

const statusText = computed(() => {
  if (loading.value) return '检查中...'
  if (!healthData.value) return '连接失败'
  if (healthData.value.status === 'healthy' && healthData.value.model_loaded) {
    return '服务正常'
  }
  if (healthData.value.status === 'healthy') {
    return '模型未加载'
  }
  return '服务异常'
})

// 格式化时间
const formatTime = (date: Date): string => {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

// 健康检查
const checkHealth = async (isRetry = false): Promise<void> => {
  if (loading.value && !isRetry) return

  loading.value = true
  errorMessage.value = null

  if (!isRetry) {
    retryCount.value = 0
  }

  try {
    healthData.value = await apiService.health()
    lastCheckTime.value = formatTime(new Date())
    retryCount.value = 0
    errorMessage.value = null
  } catch (error) {
    console.error('Health check failed:', error)

    if (error instanceof ApiError) {
      errorMessage.value = error.message
    } else if (error instanceof Error) {
      errorMessage.value = error.message || '连接服务器失败'
    } else {
      errorMessage.value = '连接服务器失败'
    }

    healthData.value = null

    // 自动重试
    if (retryCount.value < maxRetries) {
      retryCount.value++
      scheduleRetry()
    }
  } finally {
    loading.value = false
  }
}

// 安排重试
const scheduleRetry = (): void => {
  if (retryTimer) {
    window.clearTimeout(retryTimer)
  }
  retryTimer = window.setTimeout(() => {
    checkHealth(true)
  }, retryDelay)
}

// 启动自动刷新
const startAutoRefresh = (): void => {
  stopAutoRefresh()
  autoRefreshTimer = window.setInterval(() => {
    checkHealth()
  }, autoRefreshInterval)
}

// 停止自动刷新
const stopAutoRefresh = (): void => {
  if (autoRefreshTimer) {
    window.clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

// 清理定时器
const cleanup = (): void => {
  if (retryTimer) {
    window.clearTimeout(retryTimer)
    retryTimer = null
  }
  stopAutoRefresh()
}

// 生命周期
const handleRefreshClick = (): void => {
  void checkHealth()
}

onMounted(() => {
  void checkHealth()
  startAutoRefresh()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.health-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 14px;
  height: 38px;
  border-radius: 999px;
}

.status-tag .is-loading {
  animation: rotate 1s linear infinite;
}

.status-icon,
.control-icon {
  font-size: 16px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.status-text {
  margin-left: 2px;
}

.refresh-button {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(241, 245, 249, 0.96));
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #334155;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.refresh-button:hover {
  color: var(--brand);
  border-color: rgba(59, 130, 246, 0.28);
  background: rgba(239, 246, 255, 0.96);
}

.refresh-button:hover {
  color: #409eff;
}

.info-icon {
  cursor: pointer;
  color: #909399;
  transition: color 0.2s ease;
  width: 34px;
  height: 34px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
}

.info-icon:hover {
  color: #409eff;
}

.health-details {
  padding: 4px 0;
}

.error-alert {
  margin-top: 12px;
}

.retry-info {
  margin-top: 12px;
  text-align: center;
}
</style>

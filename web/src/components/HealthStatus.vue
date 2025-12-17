<template>
  <div class="health-status">
    <el-tag :type="statusType" effect="dark">
      {{ statusText }}
    </el-tag>
    <el-popover placement="bottom" :width="300" trigger="hover">
      <template #reference>
        <el-icon class="info-icon">
          <InfoFilled />
        </el-icon>
      </template>
      <div v-if="healthData" class="health-details">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="服务状态">
            {{ healthData.status }}
          </el-descriptions-item>
          <el-descriptions-item label="引擎类型">
            {{ healthData.engine || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="模型状态">
            {{ healthData.model_loaded ? '已加载' : '未加载' }}
          </el-descriptions-item>
          <el-descriptions-item label="API 版本">
            {{ healthData.version || 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
import { ElDescriptions, ElDescriptionsItem, ElIcon, ElPopover, ElTag } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { apiService } from '@/services/api'
import type { HealthResponse } from '@/types/api'

const healthData = ref<HealthResponse | null>(null)
const loading = ref(false)

const statusType = computed(() => {
  if (!healthData.value) return 'info'
  return healthData.value.status === 'healthy' ? 'success' : 'danger'
})

const statusText = computed(() => {
  if (loading.value) return '检查中...'
  if (!healthData.value) return '未知'
  return healthData.value.status === 'healthy' ? '服务正常' : '服务异常'
})

const checkHealth = async () => {
  loading.value = true
  try {
    healthData.value = await apiService.health()
  } catch (error) {
    console.error('Health check failed:', error)
    healthData.value = { status: 'unhealthy' }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  checkHealth()
})
</script>

<style scoped>
.health-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  cursor: pointer;
  color: #909399;
}

.info-icon:hover {
  color: #409eff;
}

.health-details {
  padding: 8px;
}
</style>

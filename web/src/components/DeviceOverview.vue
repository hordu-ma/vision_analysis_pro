<template>
  <el-card class="device-overview-card">
    <template #header>
      <div class="card-header">
        <span>设备概览</span>
        <el-button text @click="emit('refresh')">刷新</el-button>
      </div>
    </template>

    <div v-if="!devices.length" class="empty-state">
      <div class="empty-icon">◎</div>
      <p>暂无设备上报记录</p>
    </div>

    <el-table v-else :data="devices" stripe>
      <el-table-column prop="device_id" label="设备 ID" min-width="160" />
      <el-table-column label="显示名称" min-width="140">
        <template #default="scope">
          {{ scope.row.display_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="站点" min-width="120">
        <template #default="scope">
          {{ scope.row.site_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="batch_count" label="批次数" width="90" />
      <el-table-column prop="result_count" label="结果数" width="90" />
      <el-table-column prop="total_detections" label="检测数" width="90" />
      <el-table-column label="最近批次" min-width="180">
        <template #default="scope">
          <el-button link type="primary" @click="emit('select-device', scope.row.device_id)">
            {{ scope.row.last_batch_id }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="最近上报" min-width="160">
        <template #default="scope">
          {{ formatTime(scope.row.last_report_time) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button link type="primary" @click="emit('edit-device', scope.row.device_id)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElTable, ElTableColumn } from 'element-plus'
import type { ReportDeviceSummary } from '@/types/api'

defineProps<{
  devices: ReportDeviceSummary[]
}>()

const emit = defineEmits<{
  refresh: []
  'select-device': [deviceId: string]
  'edit-device': [deviceId: string]
}>()

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}
</script>

<style scoped>
.device-overview-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.device-overview-card :deep(.el-button.is-link) {
  font-weight: 600;
}

.device-overview-card :deep(.el-card__header) {
  padding-bottom: 14px;
}

.empty-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  gap: 12px;
  color: var(--text-muted);
  text-align: center;
}

.empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
  color: #0f766e;
  font-size: 22px;
}
</style>

<template>
  <el-card class="device-overview-card">
    <template #header>
      <div class="card-header">
        <span>设备概览</span>
        <el-button text @click="emit('refresh')">刷新</el-button>
      </div>
    </template>

    <el-empty v-if="!devices.length" description="暂无设备上报记录" />

    <el-table v-else :data="devices" stripe>
      <el-table-column prop="device_id" label="设备 ID" min-width="160" />
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
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElEmpty, ElTable, ElTableColumn } from 'element-plus'
import type { ReportDeviceSummary } from '@/types/api'

defineProps<{
  devices: ReportDeviceSummary[]
}>()

const emit = defineEmits<{
  refresh: []
  'select-device': [deviceId: string]
}>()

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}
</script>

<style scoped>
.device-overview-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

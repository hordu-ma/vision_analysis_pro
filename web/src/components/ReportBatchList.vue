<template>
  <el-card class="batch-list-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span>历史批次</span>
          <el-tag v-if="activeDeviceId" size="small" type="info">设备: {{ activeDeviceId }}</el-tag>
        </div>
        <div class="header-actions">
          <el-button v-if="activeDeviceId" text @click="emit('clear-filter')">清除筛选</el-button>
          <el-button text @click="emit('refresh')">刷新</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!batches.length" description="暂无批次记录" />

    <el-table v-else :data="batches" stripe>
      <el-table-column label="批次 ID" min-width="180">
        <template #default="scope">
          <el-button link type="primary" @click="emit('view-detail', scope.row.batch_id)">
            {{ scope.row.batch_id }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="device_id" label="设备 ID" min-width="140" />
      <el-table-column prop="result_count" label="结果数" width="90" />
      <el-table-column prop="total_detections" label="检测数" width="90" />
      <el-table-column label="上报时间" min-width="160">
        <template #default="scope">
          {{ formatTime(scope.row.report_time) }}
        </template>
      </el-table-column>
      <el-table-column label="接收时间" min-width="160">
        <template #default="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElEmpty, ElTable, ElTableColumn, ElTag } from 'element-plus'
import type { ReportBatchSummary } from '@/types/api'

defineProps<{
  batches: ReportBatchSummary[]
  activeDeviceId?: string
}>()

const emit = defineEmits<{
  refresh: []
  'clear-filter': []
  'view-detail': [batchId: string]
}>()

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}
</script>

<style scoped>
.batch-list-card {
  margin-bottom: 24px;
}

.card-header,
.header-left,
.header-actions {
  display: flex;
  align-items: center;
}

.card-header {
  justify-content: space-between;
  gap: 12px;
}

.header-left,
.header-actions {
  gap: 8px;
}
</style>

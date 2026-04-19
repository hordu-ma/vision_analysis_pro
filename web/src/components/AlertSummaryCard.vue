<template>
  <el-card class="alert-summary-card">
    <template #header>
      <div class="card-header">
        <span>告警摘要</span>
        <el-button text @click="emit('refresh')">刷新</el-button>
      </div>
    </template>

    <div v-if="!summary" class="empty-state">
      <div class="empty-icon">◔</div>
      <p>暂无告警摘要</p>
    </div>

    <el-row v-else :gutter="12">
      <el-col :span="8">
        <el-statistic :value="summary.stale_device_count">
          <template #title>离线<br />设备</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic :value="summary.failed_task_count">
          <template #title>失败<br />任务</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic :value="summary.partial_failed_task_count">
          <template #title>部分<br />失败</template>
        </el-statistic>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElCol, ElRow, ElStatistic } from 'element-plus'
import type { AlertSummaryResponse } from '@/types/api'

defineProps<{
  summary: AlertSummaryResponse | null
}>()

const emit = defineEmits<{
  refresh: []
}>()
</script>

<style scoped>
.alert-summary-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.alert-summary-card :deep(.el-statistic) {
  padding: 18px 16px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.alert-summary-card :deep(.el-card__header) {
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
  color: var(--brand);
  font-size: 22px;
}
</style>

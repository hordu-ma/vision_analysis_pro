<template>
  <el-card class="alert-summary-card">
    <template #header>
      <div class="card-header">
        <span>告警摘要</span>
        <el-button text @click="emit('refresh')">刷新</el-button>
      </div>
    </template>

    <el-empty v-if="!summary" description="暂无告警摘要" />

    <el-row v-else :gutter="12">
      <el-col :span="8">
        <el-statistic title="离线设备" :value="summary.stale_device_count" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="失败任务" :value="summary.failed_task_count" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="部分失败" :value="summary.partial_failed_task_count" />
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElCol, ElEmpty, ElRow, ElStatistic } from 'element-plus'
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
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

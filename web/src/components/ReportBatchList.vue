<template>
  <section class="batch-history product-shell-card">
    <WorkspaceSectionHeader
      title="历史批次"
      caption="保留已接收上报记录，强调设备来源、缺陷总量与时间线。"
    >
      <template #actions>
        <span v-if="activeDeviceId" class="filter-chip">{{ activeDeviceId }}</span>
        <WorkspaceActionButton
          v-if="activeDeviceId"
          label="清除筛选"
          icon="archive-stack"
          tone="subtle"
          compact
          @click="emit('clear-filter')"
        />
        <WorkspaceActionButton label="刷新" icon="spark-refresh" compact @click="emit('refresh')" />
      </template>
    </WorkspaceSectionHeader>

    <div v-if="!batches.length" class="empty-state">
      <div class="empty-icon">◎</div>
      <p>暂无批次记录</p>
    </div>

    <div v-else class="record-list">
      <WorkspaceRecordItem
        v-for="batch in batches"
        :key="batch.batch_id"
        :title="batchTitle(batch)"
        :description="batchSummary(batch)"
        :meta="batchMeta(batch)"
        :badge="batchIndex(batch)"
        badge-tone="neutral"
        @select="emit('view-detail', batch.batch_id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import WorkspaceRecordItem from '@/components/WorkspaceRecordItem.vue'
import WorkspaceActionButton from '@/components/WorkspaceActionButton.vue'
import WorkspaceSectionHeader from '@/components/WorkspaceSectionHeader.vue'
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
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const batchSummary = (batch: ReportBatchSummary) => {
  if (batch.total_detections > 0) {
    return `来自 ${batch.device_id} 的巡检批次，已接收 ${batch.result_count} 帧结果，累计识别 ${batch.total_detections} 项缺陷。`
  }
  return `来自 ${batch.device_id} 的巡检批次，已接收 ${batch.result_count} 帧结果，当前未记录到缺陷项。`
}

const batchTitle = (batch: ReportBatchSummary) => {
  return `巡检批次 ${formatTime(batch.report_time)}`
}

const batchMeta = (batch: ReportBatchSummary) => {
  return [
    `${batch.result_count} 帧结果`,
    `${batch.total_detections} 项缺陷`,
    `上报 ${formatTime(batch.report_time)}`,
    `入库 ${formatTime(batch.created_at)}`
  ]
}

const batchIndex = (batch: ReportBatchSummary) => {
  const match = batch.device_id.match(/(\d+)$/)
  const raw = match?.[1] ?? ''
  return raw ? raw.padStart(2, '0') : ''
}
</script>

<style scoped>
.batch-history {
  height: 100%;
  padding: 20px;
}

.ghost-button,
.filter-chip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
}

.batch-history :deep(.workspace-action) {
  min-height: 32px;
}

.filter-chip {
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
  color: var(--text-secondary);
}

.ghost-button {
  border: 1px solid var(--border-soft);
  background: rgba(255, 255, 255, 0.82);
  color: var(--text-secondary);
  cursor: pointer;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  min-height: 200px;
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

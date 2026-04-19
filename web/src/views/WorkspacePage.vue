<template>
  <div class="workspace-page">
    <section class="workspace-overview">
      <div class="overview-copy">
        <p class="overview-kicker">Workspace</p>
        <h3>检测发起、批次查看、任务重看</h3>
        <p>首屏聚焦交付主流程。</p>
      </div>
      <div class="overview-stats">
        <div class="overview-stat">
          <span>历史任务</span>
          <strong>{{ taskHistory.length }}</strong>
        </div>
        <div class="overview-stat">
          <span>历史批次</span>
          <strong>{{ batches.length }}</strong>
        </div>
        <div class="overview-stat subtle">
          <span>设备筛选</span>
          <strong>{{ selectedDeviceId || '全部' }}</strong>
        </div>
      </div>
    </section>

    <section class="workspace-main">
      <ImageUpload
        @result="emit('result', $event)"
        @batch-result="emit('batch-result', $event)"
        @batch-task="emit('batch-task', $event)"
      />
      <DetectionResult :result="detectionResult" />
      <BatchTaskStatus
        :task="batchTask"
        @retry="emit('retry-task', $event)"
        @retry-failed="emit('retry-failed-task', $event)"
        @rerun="emit('rerun-task', $event)"
        @export="emit('export-task-csv', $event)"
        @detail="emit('open-task', $event)"
      />
      <BatchDetectionResult
        :result="batchDetectionResult"
        :task-id="batchTask ? batchTask.task_id : undefined"
        @export="emit('export-task-csv', $event)"
        @detail="emit('open-task', $event)"
      />
    </section>

    <el-row :gutter="20" class="workspace-secondary">
      <el-col :lg="12" :xs="24">
        <ReportBatchList
          :batches="batches"
          :active-device-id="selectedDeviceId || undefined"
          @refresh="emit('refresh-reports')"
          @clear-filter="emit('clear-device-filter')"
          @view-detail="emit('open-batch', $event)"
        />
      </el-col>
      <el-col :lg="12" :xs="24">
        <TaskHistoryList
          :tasks="taskHistory"
          :status-filter="taskStatusFilter"
          @refresh="emit('refresh-tasks')"
          @select="emit('open-task', $event)"
          @retry="emit('retry-task', $event)"
          @retry-failed="emit('retry-failed-task', $event)"
          @rerun="emit('rerun-task', $event)"
          @export="emit('export-task-csv', $event)"
          @delete="emit('delete-task', $event)"
          @cleanup="emit('cleanup-tasks', $event)"
          @update:status-filter="emit('update:task-status-filter', $event)"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ElCol, ElRow } from 'element-plus'
import BatchDetectionResult from '@/components/BatchDetectionResult.vue'
import BatchTaskStatus from '@/components/BatchTaskStatus.vue'
import DetectionResult from '@/components/DetectionResult.vue'
import ImageUpload from '@/components/ImageUpload.vue'
import ReportBatchList from '@/components/ReportBatchList.vue'
import TaskHistoryList from '@/components/TaskHistoryList.vue'
import type {
  BatchInferenceResponse,
  InferenceResponse,
  InferenceTaskDetailResponse,
  InferenceTaskResponse,
  InferenceTaskStatus,
  ReportBatchSummary
} from '@/types/api'

defineProps<{
  detectionResult: InferenceResponse | null
  batchDetectionResult: BatchInferenceResponse | null
  batchTask: InferenceTaskDetailResponse | null
  taskHistory: InferenceTaskResponse[]
  taskStatusFilter: InferenceTaskStatus | ''
  batches: ReportBatchSummary[]
  selectedDeviceId: string
}>()

const emit = defineEmits<{
  result: [data: InferenceResponse]
  'batch-result': [data: BatchInferenceResponse]
  'batch-task': [data: InferenceTaskResponse]
  'refresh-reports': []
  'refresh-tasks': []
  'retry-task': [taskId: string]
  'retry-failed-task': [taskId: string]
  'rerun-task': [taskId: string]
  'export-task-csv': [taskId: string]
  'open-task': [taskId: string]
  'open-batch': [batchId: string]
  'delete-task': [taskId: string]
  'cleanup-tasks': [status: 'completed' | 'failed' | null]
  'clear-device-filter': []
  'update:task-status-filter': [status: InferenceTaskStatus | '']
}>()
</script>

<style scoped>
.workspace-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workspace-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.9fr);
  gap: 18px;
  padding: 4px 0 0;
}

.overview-kicker {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  color: var(--brand);
  font-weight: 700;
}

.overview-copy h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  white-space: nowrap;
}

.overview-copy p:last-child {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-self: center;
}

.overview-stat {
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
}

.overview-stat.subtle {
  background: rgba(29, 78, 216, 0.06);
}

.overview-stat span,
.overview-stat strong {
  display: block;
}

.overview-stat span {
  color: var(--text-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.overview-stat strong {
  font-size: 16px;
  line-height: 1;
  white-space: nowrap;
}

.workspace-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0 0 6px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.workspace-secondary {
  margin-top: 0;
}

.workspace-secondary :deep(.el-col) {
  display: flex;
}

.workspace-secondary :deep(.product-shell-card) {
  width: 100%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(248, 250, 252, 0.82));
}

@media (max-width: 960px) {
  .workspace-overview {
    grid-template-columns: 1fr;
  }

  .overview-stats {
    grid-template-columns: 1fr;
  }
}
</style>

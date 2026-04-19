<template>
  <el-row :gutter="24">
    <el-col :lg="14" :xs="24">
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
    </el-col>
    <el-col :lg="10" :xs="24">
      <ReportBatchList
        :batches="batches"
        :active-device-id="selectedDeviceId || undefined"
        @refresh="emit('refresh-reports')"
        @clear-filter="emit('clear-device-filter')"
        @view-detail="emit('open-batch', $event)"
      />
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

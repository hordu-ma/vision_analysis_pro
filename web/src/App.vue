<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <div class="header-left">
          <h1>Vision Analysis Pro</h1>
          <el-radio-group v-model="activeView" size="small">
            <el-radio-button label="workspace">任务工作台</el-radio-button>
            <el-radio-button label="devices">设备管理</el-radio-button>
          </el-radio-group>
        </div>
        <HealthStatus />
      </el-header>
      <el-main>
        <el-row v-if="activeView === 'workspace'" :gutter="24">
          <el-col :lg="14" :xs="24">
            <ImageUpload
              @result="handleResult"
              @batch-result="handleBatchResult"
              @batch-task="handleBatchTask"
            />
            <DetectionResult :result="detectionResult" />
            <BatchTaskStatus
              :task="batchTask"
              @retry="handleRetryTask"
              @retry-failed="handleRetryFailedTask"
              @rerun="handleRerunTask"
              @export="handleExportTaskCsv"
              @detail="openTaskHistory"
            />
            <BatchDetectionResult
              :result="batchDetectionResult"
              :task-id="batchTask ? batchTask.task_id : undefined"
              @export="handleExportTaskCsv"
              @detail="openTaskHistory"
            />
          </el-col>
          <el-col :lg="10" :xs="24">
            <AlertSummaryCard :summary="alertSummary" @refresh="loadAlertSummary" />
            <DeviceOverview
              :devices="devices"
              @refresh="loadReportData"
              @select-device="handleDeviceSelect"
              @edit-device="openDeviceMetadata"
            />
            <ReportBatchList
              :batches="batches"
              :active-device-id="selectedDeviceId || undefined"
              @refresh="loadReportData"
              @clear-filter="clearDeviceFilter"
              @view-detail="openBatchDetail"
            />
            <TaskHistoryList
              :tasks="taskHistory"
              :status-filter="taskStatusFilter"
              @refresh="loadTaskHistory"
              @select="openTaskHistory"
              @retry="handleRetryTask"
              @retry-failed="handleRetryFailedTask"
              @rerun="handleRerunTask"
              @export="handleExportTaskCsv"
              @delete="handleDeleteTask"
              @cleanup="handleCleanupTasks"
              @update:status-filter="handleTaskStatusFilterChange"
            />
          </el-col>
        </el-row>
        <DeviceManagementView
          v-else
          :summary="alertSummary"
          :devices="devices"
          :logs="auditLogs"
          @refresh-alerts="loadAlertSummary"
          @refresh-devices="loadReportData"
          @refresh-audit-logs="loadAuditLogs"
          @select-device="handleDeviceSelect"
          @edit-device="openDeviceMetadata"
        />
        <ReportDetailDrawer
          :visible="detailVisible"
          :report="selectedReport"
          @close="detailVisible = false"
          @export="handleExportCsv"
          @save-review="handleSaveReview"
        />
        <TaskDetailDrawer
          :visible="taskDetailVisible"
          :task="batchTask"
          @close="taskDetailVisible = false"
          @retry-failed="handleRetryFailedTask"
          @export-csv="handleExportTaskCsv"
          @export-json="handleExportTaskJson"
          @export-zip="handleExportTaskZip"
        />
        <DeviceMetadataDrawer
          :visible="deviceDrawerVisible"
          :device-id="editingDeviceId"
          :device="editingDevice"
          @close="deviceDrawerVisible = false"
          @save="handleSaveDeviceMetadata"
        />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import {
  ElCol,
  ElContainer,
  ElHeader,
  ElMain,
  ElRadioButton,
  ElRadioGroup,
  ElRow
} from 'element-plus'
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
const DeviceManagementView = defineAsyncComponent(
  () => import('@/components/DeviceManagementView.vue')
)
const BatchDetectionResult = defineAsyncComponent(
  () => import('@/components/BatchDetectionResult.vue')
)
const BatchTaskStatus = defineAsyncComponent(() => import('@/components/BatchTaskStatus.vue'))
const DeviceMetadataDrawer = defineAsyncComponent(
  () => import('@/components/DeviceMetadataDrawer.vue')
)
const DetectionResult = defineAsyncComponent(() => import('@/components/DetectionResult.vue'))
import HealthStatus from '@/components/HealthStatus.vue'
import ImageUpload from '@/components/ImageUpload.vue'
import ReportBatchList from '@/components/ReportBatchList.vue'
const ReportDetailDrawer = defineAsyncComponent(() => import('@/components/ReportDetailDrawer.vue'))
const TaskDetailDrawer = defineAsyncComponent(() => import('@/components/TaskDetailDrawer.vue'))
import TaskHistoryList from '@/components/TaskHistoryList.vue'
import { apiService } from '@/services/api'
import type {
  InferenceResponse,
  BatchInferenceResponse,
  AlertSummaryResponse,
  AuditLogResponse,
  InferenceTaskDetailResponse,
  InferenceTaskResponse,
  InferenceTaskStatus,
  ReportBatchSummary,
  ReportDeviceMetadataRequest,
  ReportDeviceSummary,
  ReportRecordResponse,
  ReportReviewRequest
} from '@/types/api'

const detectionResult = ref<InferenceResponse | null>(null)
const activeView = ref<'workspace' | 'devices'>('workspace')
const batchDetectionResult = ref<BatchInferenceResponse | null>(null)
const batchTask = ref<InferenceTaskDetailResponse | null>(null)
const taskHistory = ref<InferenceTaskResponse[]>([])
const taskStatusFilter = ref<InferenceTaskStatus | ''>('')
const alertSummary = ref<AlertSummaryResponse | null>(null)
const auditLogs = ref<AuditLogResponse[]>([])
const batches = ref<ReportBatchSummary[]>([])
const devices = ref<ReportDeviceSummary[]>([])
const selectedDeviceId = ref('')
const deviceDrawerVisible = ref(false)
const editingDeviceId = ref('')
const detailVisible = ref(false)
const taskDetailVisible = ref(false)
const selectedReport = ref<ReportRecordResponse | null>(null)

const editingDevice = computed(() => {
  return devices.value.find(item => item.device_id === editingDeviceId.value) || null
})

const handleResult = (data: InferenceResponse) => {
  batchTask.value = null
  batchDetectionResult.value = null
  detectionResult.value = data
}

const handleBatchResult = (data: BatchInferenceResponse) => {
  batchTask.value = null
  detectionResult.value = null
  batchDetectionResult.value = data
}

let taskPollTimer: number | null = null

const stopTaskPolling = () => {
  if (taskPollTimer !== null) {
    window.clearTimeout(taskPollTimer)
    taskPollTimer = null
  }
}

const pollBatchTask = async (taskId: string) => {
  try {
    const task = await apiService.getBatchTask(taskId)
    batchTask.value = task

    if (task.status === 'completed' || task.status === 'partial_failed') {
      batchDetectionResult.value = {
        files: task.results,
        metadata: task.metadata
      }
      await loadTaskHistory()
      return
    }

    if (task.status === 'failed') {
      await loadTaskHistory()
      return
    }

    taskPollTimer = window.setTimeout(() => {
      void pollBatchTask(taskId)
    }, 800)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleBatchTask = (task: InferenceTaskResponse) => {
  detectionResult.value = null
  batchDetectionResult.value = null
  batchTask.value = null
  stopTaskPolling()
  void loadTaskHistory()
  void pollBatchTask(task.task_id)
}

const loadTaskHistory = async () => {
  try {
    taskHistory.value = await apiService.listBatchTasks(10, taskStatusFilter.value)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const selectTask = (task: InferenceTaskDetailResponse) => {
  batchTask.value = task
  detectionResult.value = null

  if (task.status === 'completed' || task.status === 'partial_failed') {
    batchDetectionResult.value = {
      files: task.results,
      metadata: task.metadata
    }
    return
  }

  batchDetectionResult.value = null
}

const openTaskHistory = async (taskId: string) => {
  stopTaskPolling()
  try {
    const task = await apiService.getBatchTask(taskId)
    selectTask(task)
    taskDetailVisible.value = true
    if (task.status === 'running' || task.status === 'pending') {
      void pollBatchTask(taskId)
    }
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const startTaskFromResponse = (task: InferenceTaskResponse) => {
  stopTaskPolling()
  batchTask.value = null
  batchDetectionResult.value = null
  taskDetailVisible.value = false
  void loadTaskHistory()
  void pollBatchTask(task.task_id)
}

const handleRetryTask = async (taskId: string) => {
  try {
    const task = await apiService.retryBatchTask(taskId)
    startTaskFromResponse(task)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleRerunTask = async (taskId: string) => {
  try {
    const task = await apiService.rerunBatchTask(taskId)
    startTaskFromResponse(task)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleRetryFailedTask = async (taskId: string) => {
  try {
    const task = await apiService.retryFailedBatchTask(taskId)
    startTaskFromResponse(task)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleTaskStatusFilterChange = (status: InferenceTaskStatus | '') => {
  taskStatusFilter.value = status
  void loadTaskHistory()
}

const handleExportTaskCsv = async (taskId: string) => {
  await downloadTaskExport(taskId, 'csv')
}

const handleExportTaskJson = async (taskId: string) => {
  await downloadTaskExport(taskId, 'json')
}

const handleExportTaskZip = async (taskId: string) => {
  await downloadTaskExport(taskId, 'zip')
}

const downloadTaskExport = async (taskId: string, format: 'csv' | 'json' | 'zip') => {
  try {
    const blob =
      format === 'csv'
        ? await apiService.exportBatchTaskCsv(taskId)
        : format === 'json'
          ? await apiService.exportBatchTaskJson(taskId)
          : await apiService.exportBatchTaskZip(taskId)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${taskId}.${format}`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleDeleteTask = async (taskId: string) => {
  try {
    await apiService.deleteBatchTask(taskId)
    if (batchTask.value?.task_id === taskId) {
      batchTask.value = null
      batchDetectionResult.value = null
    }
    await loadTaskHistory()
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleCleanupTasks = async (status: 'completed' | 'failed' | null) => {
  try {
    const result = await apiService.cleanupBatchTasks(status ?? '')
    const activeStatus = batchTask.value?.status
    if (
      batchTask.value &&
      activeStatus &&
      (activeStatus === 'completed' || activeStatus === 'failed') &&
      (!status || activeStatus === status)
    ) {
      batchTask.value = null
      batchDetectionResult.value = null
    }
    await loadTaskHistory()
    if (result.deleted_count === 0) {
      return
    }
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const loadReportData = async () => {
  try {
    const [deviceResponse, batchResponse] = await Promise.all([
      apiService.listReportDevices(10),
      apiService.listReportBatches(20, selectedDeviceId.value || undefined)
    ])
    devices.value = deviceResponse.items
    batches.value = batchResponse.items
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const loadAlertSummary = async () => {
  try {
    alertSummary.value = await apiService.getAlertSummary()
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const loadAuditLogs = async () => {
  try {
    auditLogs.value = await apiService.listAuditLogs(20)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleDeviceSelect = (deviceId: string) => {
  selectedDeviceId.value = deviceId
  void loadReportData()
}

const clearDeviceFilter = () => {
  selectedDeviceId.value = ''
  void loadReportData()
}

const openDeviceMetadata = (deviceId: string) => {
  editingDeviceId.value = deviceId
  deviceDrawerVisible.value = true
}

const handleSaveDeviceMetadata = async (payload: ReportDeviceMetadataRequest) => {
  if (!editingDeviceId.value) return

  try {
    await apiService.updateReportDeviceMetadata(editingDeviceId.value, payload)
    deviceDrawerVisible.value = false
    await loadReportData()
    await loadAuditLogs()
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const openBatchDetail = async (batchId: string) => {
  try {
    selectedReport.value = await apiService.getReport(batchId)
    detailVisible.value = true
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleSaveReview = async (frameId: number, payload: ReportReviewRequest) => {
  if (!selectedReport.value) return

  try {
    await apiService.updateReportReview(selectedReport.value.batch_id, frameId, payload)
    selectedReport.value = await apiService.getReport(selectedReport.value.batch_id)
    await loadReportData()
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleExportCsv = async (batchId: string) => {
  try {
    const blob = await apiService.exportReportCsv(batchId)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${batchId}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

onMounted(() => {
  void loadReportData()
  void loadAlertSummary()
  void loadAuditLogs()
  void loadTaskHistory()
})

onBeforeUnmount(() => {
  stopTaskPolling()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.el-main {
  padding: 40px 20px;
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .el-main {
    padding: 24px 12px;
  }
}
</style>

<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <h1>Vision Analysis Pro</h1>
        <HealthStatus />
      </el-header>
      <el-main>
        <el-row :gutter="24">
          <el-col :lg="14" :xs="24">
            <ImageUpload
              @result="handleResult"
              @batch-result="handleBatchResult"
              @batch-task="handleBatchTask"
            />
            <DetectionResult :result="detectionResult" />
            <BatchTaskStatus :task="batchTask" />
            <BatchDetectionResult :result="batchDetectionResult" />
          </el-col>
          <el-col :lg="10" :xs="24">
            <DeviceOverview
              :devices="devices"
              @refresh="loadReportData"
              @select-device="handleDeviceSelect"
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
              @refresh="loadTaskHistory"
              @select="openTaskHistory"
            />
          </el-col>
        </el-row>
        <ReportDetailDrawer
          :visible="detailVisible"
          :report="selectedReport"
          @close="detailVisible = false"
          @export="handleExportCsv"
          @save-review="handleSaveReview"
        />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ElContainer, ElHeader, ElMain, ElRow, ElCol } from 'element-plus'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import DeviceOverview from '@/components/DeviceOverview.vue'
import BatchDetectionResult from '@/components/BatchDetectionResult.vue'
import BatchTaskStatus from '@/components/BatchTaskStatus.vue'
import DetectionResult from '@/components/DetectionResult.vue'
import HealthStatus from '@/components/HealthStatus.vue'
import ImageUpload from '@/components/ImageUpload.vue'
import ReportBatchList from '@/components/ReportBatchList.vue'
import ReportDetailDrawer from '@/components/ReportDetailDrawer.vue'
import TaskHistoryList from '@/components/TaskHistoryList.vue'
import { apiService } from '@/services/api'
import type {
  InferenceResponse,
  BatchInferenceResponse,
  InferenceTaskResponse,
  ReportBatchSummary,
  ReportDeviceSummary,
  ReportRecordResponse,
  ReportReviewRequest
} from '@/types/api'

const detectionResult = ref<InferenceResponse | null>(null)
const batchDetectionResult = ref<BatchInferenceResponse | null>(null)
const batchTask = ref<InferenceTaskResponse | null>(null)
const taskHistory = ref<InferenceTaskResponse[]>([])
const batches = ref<ReportBatchSummary[]>([])
const devices = ref<ReportDeviceSummary[]>([])
const selectedDeviceId = ref('')
const detailVisible = ref(false)
const selectedReport = ref<ReportRecordResponse | null>(null)

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

    if (task.status === 'completed') {
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
  batchTask.value = task
  stopTaskPolling()
  void loadTaskHistory()
  void pollBatchTask(task.task_id)
}

const loadTaskHistory = async () => {
  try {
    taskHistory.value = await apiService.listBatchTasks(10)
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const openTaskHistory = async (taskId: string) => {
  stopTaskPolling()
  try {
    const task = await apiService.getBatchTask(taskId)
    batchTask.value = task
    detectionResult.value = null

    if (task.status === 'completed') {
      batchDetectionResult.value = {
        files: task.results,
        metadata: task.metadata
      }
      return
    }

    batchDetectionResult.value = null
    if (task.status === 'running' || task.status === 'pending') {
      void pollBatchTask(taskId)
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

const handleDeviceSelect = (deviceId: string) => {
  selectedDeviceId.value = deviceId
  void loadReportData()
}

const clearDeviceFilter = () => {
  selectedDeviceId.value = ''
  void loadReportData()
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

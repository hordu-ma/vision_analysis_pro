<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">
          <span></span>
        </div>
        <div>
          <p class="brand-en">Vision Analysis Pro</p>
          <h1>基础设施视觉智能运维平台</h1>
        </div>
      </div>

      <nav class="product-nav">
        <button
          class="nav-item"
          :class="{ active: activeRoute === '/workspace' }"
          @click="handleRouteChange('/workspace')"
        >
          <span class="nav-kicker">01</span>
          <span>
            <strong>任务工作台</strong>
            <small>上传、检测、复跑与结果交付</small>
          </span>
        </button>
        <button
          class="nav-item"
          :class="{ active: activeRoute === '/devices' }"
          @click="handleRouteChange('/devices')"
        >
          <span class="nav-kicker">02</span>
          <span>
            <strong>设备管理</strong>
            <small>设备元数据、告警摘要与审计记录</small>
          </span>
        </button>
      </nav>

      <div class="sidebar-telemetry" aria-label="系统能力摘要">
        <div>
          <span>ENGINE</span>
          <strong>YOLO / ONNX</strong>
        </div>
        <div>
          <span>FLOW</span>
          <strong>Review Ready</strong>
        </div>
      </div>

      <div class="sidebar-footnote product-shell-card">
        <p class="section-title">操作者</p>
        <p class="section-caption">所有变更与设备维护都会进入审计日志</p>
        <el-input
          v-model="actorName"
          placeholder="输入操作人名称"
          size="large"
          @change="handleActorChange"
        />
      </div>
    </aside>

    <main class="app-main">
      <section class="topbar product-shell-card">
        <div>
          <p class="topbar-kicker">
            {{ activeRoute === '/workspace' ? 'Workspace' : 'Device Control' }}
          </p>
          <h2 class="topbar-title">
            {{ activeRoute === '/workspace' ? '任务工作台' : '设备与审计管理台' }}
          </h2>
          <p class="topbar-subtitle">
            {{
              activeRoute === '/workspace'
                ? '检测、批次与任务的交付工作流。'
                : '设备、告警与审计的统一运维视图。'
            }}
          </p>
        </div>
        <div class="ops-strip" aria-hidden="true">
          <span class="ops-node active"></span>
          <span class="ops-line"></span>
          <span class="ops-node"></span>
          <span class="ops-line"></span>
          <span class="ops-node"></span>
        </div>
        <div class="topbar-status">
          <div class="status-chip">
            <span class="chip-label">操作者</span>
            <strong>{{ actorName }}</strong>
          </div>
          <div class="status-chip">
            <span class="chip-label">当前视图</span>
            <strong>{{ activeRoute === '/workspace' ? '任务工作台' : '设备管理' }}</strong>
          </div>
          <div class="health-chip product-shell-card">
            <HealthStatus />
          </div>
        </div>
      </section>

      <section class="content-surface product-shell-card">
        <router-view v-slot="{ Component }">
          <component
            :is="Component"
            :detection-result="detectionResult"
            :batch-detection-result="batchDetectionResult"
            :batch-task="batchTask"
            :task-history="taskHistory"
            :task-status-filter="taskStatusFilter"
            :task-limit="taskLimit"
            :task-offset="taskOffset"
            :batches="batches"
            :batch-total="batchTotal"
            :batch-limit="batchLimit"
            :batch-offset="batchOffset"
            :selected-device-id="selectedDeviceId"
            :summary="alertSummary"
            :devices="devices"
            :device-total="deviceTotal"
            :device-limit="deviceLimit"
            :device-offset="deviceOffset"
            :logs="auditLogs"
            :audit-log-total="auditLogTotal"
            :audit-log-limit="auditLogLimit"
            :audit-log-offset="auditLogOffset"
            :actor-filter="auditActorFilter"
            @result="handleResult"
            @batch-result="handleBatchResult"
            @batch-task="handleBatchTask"
            @refresh-reports="loadReportData"
            @page-reports="handleReportPageChange"
            @refresh-tasks="loadTaskHistory"
            @page-tasks="handleTaskPageChange"
            @retry-task="handleRetryTask"
            @retry-failed-task="handleRetryFailedTask"
            @rerun-task="handleRerunTask"
            @export-task-csv="handleExportTaskCsv"
            @open-task="openTaskHistory"
            @open-batch="openBatchDetail"
            @delete-task="handleDeleteTask"
            @cleanup-tasks="handleCleanupTasks"
            @clear-device-filter="clearDeviceFilter"
            @update:task-status-filter="handleTaskStatusFilterChange"
            @refresh-alerts="loadAlertSummary"
            @refresh-devices="loadReportData"
            @page-devices="handleDevicePageChange"
            @refresh-audit-logs="loadAuditLogs"
            @page-audit-logs="handleAuditLogPageChange"
            @select-device="handleDeviceSelect"
            @edit-device="openDeviceMetadata"
            @update:actor-filter="handleAuditActorFilterChange"
          />
        </router-view>
      </section>

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
    </main>
  </div>
</template>

<script setup lang="ts">
import { ElInput } from 'element-plus'
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
const DeviceMetadataDrawer = defineAsyncComponent(
  () => import('@/components/DeviceMetadataDrawer.vue')
)
import HealthStatus from '@/components/HealthStatus.vue'
const ReportDetailDrawer = defineAsyncComponent(() => import('@/components/ReportDetailDrawer.vue'))
const TaskDetailDrawer = defineAsyncComponent(() => import('@/components/TaskDetailDrawer.vue'))
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
const batchDetectionResult = ref<BatchInferenceResponse | null>(null)
const batchTask = ref<InferenceTaskDetailResponse | null>(null)
const taskHistory = ref<InferenceTaskResponse[]>([])
const taskStatusFilter = ref<InferenceTaskStatus | ''>('')
const taskLimit = 10
const taskOffset = ref(0)
const alertSummary = ref<AlertSummaryResponse | null>(null)
const auditLogs = ref<AuditLogResponse[]>([])
const actorName = ref('liguo ma')
const auditActorFilter = ref('')
const batches = ref<ReportBatchSummary[]>([])
const batchLimit = 20
const batchOffset = ref(0)
const batchTotal = ref(0)
const devices = ref<ReportDeviceSummary[]>([])
const deviceLimit = 10
const deviceOffset = ref(0)
const deviceTotal = ref(0)
const auditLogLimit = 20
const auditLogOffset = ref(0)
const auditLogTotal = ref(0)
const selectedDeviceId = ref('')
const deviceDrawerVisible = ref(false)
const editingDeviceId = ref('')
const detailVisible = ref(false)
const taskDetailVisible = ref(false)
const selectedReport = ref<ReportRecordResponse | null>(null)
const route = useRoute()
const router = useRouter()

const activeRoute = computed(() => route.path)

const editingDevice = computed(() => {
  return devices.value.find(item => item.device_id === editingDeviceId.value) || null
})

const handleRouteChange = (path: string | number | boolean | undefined) => {
  if (typeof path === 'string') {
    void router.push(path)
  }
}

const handleActorChange = () => {
  apiService.setActor(actorName.value)
  void loadAuditLogs()
}

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
    taskHistory.value = await apiService.listBatchTasks(
      taskLimit,
      taskStatusFilter.value,
      taskOffset.value
    )
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
  taskOffset.value = 0
  void loadTaskHistory()
}

const handleTaskPageChange = (offset: number) => {
  taskOffset.value = offset
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
      apiService.listReportDevices(deviceLimit, deviceOffset.value),
      apiService.listReportBatches(
        batchLimit,
        selectedDeviceId.value || undefined,
        batchOffset.value
      )
    ])
    devices.value = deviceResponse.items
    deviceTotal.value = deviceResponse.total ?? deviceResponse.count
    batches.value = batchResponse.items
    batchTotal.value = batchResponse.total ?? batchResponse.count
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleReportPageChange = (offset: number) => {
  batchOffset.value = offset
  void loadReportData()
}

const handleDevicePageChange = (offset: number) => {
  deviceOffset.value = offset
  void loadReportData()
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
    const response = await apiService.listAuditLogs(
      auditLogLimit,
      auditActorFilter.value || undefined,
      auditLogOffset.value
    )
    auditLogs.value = response.items
    auditLogTotal.value = response.total ?? response.count
  } catch (error) {
    apiService.showError(error as Error)
  }
}

const handleAuditActorFilterChange = (actor: string) => {
  auditActorFilter.value = actor
  auditLogOffset.value = 0
  void loadAuditLogs()
}

const handleAuditLogPageChange = (offset: number) => {
  auditLogOffset.value = offset
  void loadAuditLogs()
}

const handleDeviceSelect = (deviceId: string) => {
  selectedDeviceId.value = deviceId
  batchOffset.value = 0
  void loadReportData()
}

const clearDeviceFilter = () => {
  selectedDeviceId.value = ''
  batchOffset.value = 0
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
  apiService.setActor(actorName.value)
})

onBeforeUnmount(() => {
  stopTaskPolling()
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 316px minmax(0, 1fr);
  gap: 22px;
  padding: 20px;
}

.app-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: calc(100vh - 40px);
  padding: 26px 22px;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(21, 34, 58, 0.98)),
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.04) 0,
      rgba(255, 255, 255, 0.04) 1px,
      transparent 1px,
      transparent 14px
    );
  color: rgba(255, 255, 255, 0.92);
  box-shadow: 0 26px 60px rgba(15, 23, 42, 0.24);
  position: sticky;
  top: 20px;
}

.brand-block {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding-bottom: 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.1);
}

.brand-mark {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  border-radius: 15px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.95), rgba(245, 158, 11, 0.92)), #14b8a6;
  box-shadow: 0 14px 30px rgba(20, 184, 166, 0.22);
}

.brand-mark span {
  width: 24px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.88);
  border-top: 0;
  border-radius: 0 0 10px 10px;
  position: relative;
}

.brand-mark span::before {
  content: '';
  position: absolute;
  left: 4px;
  right: 4px;
  top: -7px;
  height: 2px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 6px 0 rgba(255, 255, 255, 0.74);
}

.brand-en {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
  color: rgba(191, 219, 254, 0.8);
}

.brand-block h1 {
  margin: 0;
  font-size: 19px;
  line-height: 1.28;
  word-break: keep-all;
}

.product-nav {
  display: grid;
  gap: 8px;
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 78px;
  padding: 15px 16px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.035);
  color: inherit;
  text-align: left;
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease;
}

.nav-item::after {
  content: '';
  width: 8px;
  height: 8px;
  margin-left: auto;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.36);
}

.nav-item:hover,
.nav-item.active {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.095);
  border-color: rgba(20, 184, 166, 0.34);
}

.nav-item.active::after {
  background: #f59e0b;
  box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.12);
}

.nav-kicker {
  min-width: 34px;
  min-height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.07);
  font-size: 11px;
  line-height: 1;
  color: rgba(191, 219, 254, 0.78);
}

.nav-item strong {
  display: block;
  font-size: 15px;
  margin-bottom: 4px;
}

.nav-item small {
  display: block;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(226, 232, 240, 0.68);
}

.sidebar-telemetry {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(2, 6, 23, 0.22);
  border: 1px solid rgba(226, 232, 240, 0.08);
}

.sidebar-telemetry div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-telemetry span {
  color: rgba(203, 213, 225, 0.58);
  font-size: 10px;
  letter-spacing: 0.12em;
}

.sidebar-telemetry strong {
  color: rgba(255, 255, 255, 0.86);
  font-size: 12px;
}

.sidebar-footnote {
  margin-top: auto;
  padding: 16px;
  background: rgba(255, 255, 255, 0.075);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
}

.sidebar-footnote :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.96);
}

.app-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.topbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px auto;
  align-items: center;
  gap: 20px;
  padding: 24px 26px;
}

.topbar-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--brand);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-weight: 700;
}

.topbar-title {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
}

.topbar-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.topbar-status {
  display: flex;
  align-items: stretch;
  gap: 10px;
}

.status-chip,
.health-chip {
  min-width: 140px;
  padding: 13px 15px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-soft);
}

.chip-label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.content-surface {
  min-height: 0;
  padding: 22px;
}

.health-chip {
  display: flex;
  align-items: center;
}

.ops-strip {
  display: flex;
  align-items: center;
  justify-content: center;
}

.ops-node {
  width: 13px;
  height: 13px;
  border-radius: 999px;
  border: 2px solid rgba(20, 184, 166, 0.4);
  background: #fff;
}

.ops-node.active {
  background: #14b8a6;
  border-color: #14b8a6;
  box-shadow: 0 0 0 5px rgba(20, 184, 166, 0.12);
}

.ops-line {
  width: 54px;
  height: 2px;
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.32), rgba(245, 158, 11, 0.3));
}

@media (max-width: 1280px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .app-sidebar {
    padding: 22px;
    min-height: auto;
    position: static;
  }

  .sidebar-footnote {
    margin-top: 0;
  }
}

@media (max-width: 960px) {
  .app-shell {
    padding: 14px;
  }

  .topbar {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .topbar-status {
    width: 100%;
    flex-wrap: wrap;
  }

  .status-chip,
  .health-chip {
    flex: 1 1 180px;
  }

  .content-surface {
    padding: 18px;
  }
}
</style>

<template>
  <el-card v-if="task" class="batch-task-card">
    <template #header>
      <div class="card-header">
        <span>批量任务状态</span>
        <el-tag :type="tagType">{{ statusLabel }}</el-tag>
      </div>
    </template>

    <el-descriptions :column="2" border>
      <el-descriptions-item label="任务 ID">{{ task.task_id }}</el-descriptions-item>
      <el-descriptions-item label="图片数量">{{ task.file_count }}</el-descriptions-item>
      <el-descriptions-item label="已完成">{{ task.completed_files }}</el-descriptions-item>
      <el-descriptions-item label="进度">{{ task.progress }}%</el-descriptions-item>
    </el-descriptions>

    <div class="progress-section">
      <el-progress :percentage="task.progress" :status="progressStatus" />
    </div>

    <el-alert
      v-if="task.error"
      :title="task.error.message"
      :description="task.error.detail"
      type="error"
      show-icon
      class="task-alert"
    />

    <div class="task-actions">
      <el-button
        v-if="task.status === 'failed'"
        type="danger"
        plain
        @click="emit('retry', task.task_id)"
      >
        重试当前任务
      </el-button>
      <el-button
        v-if="task.status === 'completed'"
        type="success"
        plain
        @click="emit('rerun', task.task_id)"
      >
        复跑当前任务
      </el-button>
      <el-button
        v-if="task.status === 'completed'"
        type="primary"
        plain
        @click="emit('export', task.task_id)"
      >
        导出 CSV
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElProgress,
  ElTag
} from 'element-plus'
import { computed } from 'vue'
import type { InferenceTaskResponse } from '@/types/api'

const props = defineProps<{
  task: InferenceTaskResponse | null
}>()

const emit = defineEmits<{
  retry: [taskId: string]
  rerun: [taskId: string]
  export: [taskId: string]
}>()

const statusLabel = computed(() => {
  switch (props.task?.status) {
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '待开始'
  }
})

const tagType = computed(() => {
  switch (props.task?.status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'running':
      return 'warning'
    default:
      return 'info'
  }
})

const progressStatus = computed(() => {
  return props.task?.status === 'failed' ? 'exception' : undefined
})
</script>

<style scoped>
.batch-task-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.progress-section {
  margin-top: 20px;
}

.task-alert {
  margin-top: 16px;
}

.task-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
</style>

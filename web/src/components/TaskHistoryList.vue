<template>
  <section class="task-history product-shell-card">
    <WorkspaceSectionHeader
      title="最近任务"
      caption="保留执行状态、任务规模与可操作入口，不再使用后台式数据表。"
    >
      <template #actions>
        <el-select
          :model-value="statusFilter"
          placeholder="状态"
          size="small"
          clearable
          class="status-filter"
          @change="handleStatusChange"
        >
          <el-option label="待开始" value="pending" />
          <el-option label="执行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <div class="action-row">
          <WorkspaceActionButton
            label="清理"
            icon="archive-stack"
            tone="subtle"
            compact
            @click="emitCleanup"
          />
          <WorkspaceActionButton
            label="刷新"
            icon="spark-refresh"
            compact
            @click="emit('refresh')"
          />
        </div>
      </template>
    </WorkspaceSectionHeader>

    <div v-if="!tasks.length" class="empty-state">
      <div class="empty-icon">◌</div>
      <p>暂无批量任务</p>
    </div>

    <div v-else class="task-list">
      <WorkspaceRecordItem
        v-for="task in tasks"
        :key="task.task_id"
        :title="task.task_id"
        :description="taskSummary(task)"
        :meta="taskMeta(task)"
        @select="emit('select', task.task_id)"
      >
        <template #actions>
          <span class="status-chip" :class="`status-${task.status}`">
            {{ statusText(task.status) }}
          </span>
          <button class="inline-button" @click="emit('select', task.task_id)">查看</button>
          <button
            v-if="task.status === 'failed'"
            class="inline-button danger"
            @click="emit('retry', task.task_id)"
          >
            重试
          </button>
          <button
            v-if="task.status === 'partial_failed'"
            class="inline-button danger"
            @click="emit('retry-failed', task.task_id)"
          >
            重试失败项
          </button>
          <button
            v-if="task.status === 'completed' || task.status === 'partial_failed'"
            class="inline-button success"
            @click="emit('rerun', task.task_id)"
          >
            复跑
          </button>
          <button
            v-if="task.status === 'completed' || task.status === 'partial_failed'"
            class="inline-button"
            @click="emit('export', task.task_id)"
          >
            导出
          </button>
          <button
            v-if="task.status === 'completed' || task.status === 'failed'"
            class="inline-button subtle"
            @click="emit('delete', task.task_id)"
          >
            删除
          </button>
        </template>
      </WorkspaceRecordItem>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElOption, ElSelect } from 'element-plus'
import WorkspaceActionButton from '@/components/WorkspaceActionButton.vue'
import WorkspaceRecordItem from '@/components/WorkspaceRecordItem.vue'
import WorkspaceSectionHeader from '@/components/WorkspaceSectionHeader.vue'
import type { InferenceTaskResponse, InferenceTaskStatus } from '@/types/api'

const props = defineProps<{
  tasks: InferenceTaskResponse[]
  statusFilter: InferenceTaskStatus | ''
}>()

const emit = defineEmits<{
  refresh: []
  select: [taskId: string]
  retry: [taskId: string]
  'retry-failed': [taskId: string]
  rerun: [taskId: string]
  export: [taskId: string]
  delete: [taskId: string]
  cleanup: [status: 'completed' | 'failed' | null]
  'update:statusFilter': [status: InferenceTaskStatus | '']
}>()

const handleStatusChange = (value: InferenceTaskStatus | '' | undefined) => {
  emit('update:statusFilter', value ?? '')
}

const emitCleanup = () => {
  const status = statusFilterValue()
  emit('cleanup', status)
}

const statusFilterValue = (): 'completed' | 'failed' | null => {
  if (props.statusFilter === 'completed' || props.statusFilter === 'failed') {
    return props.statusFilter
  }
  return null
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const statusText = (status: string): string => {
  switch (status) {
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'partial_failed':
      return '部分失败'
    default:
      return '待开始'
  }
}

const taskSummary = (task: InferenceTaskResponse): string => {
  if (task.status === 'completed') return '任务已完成，可查看详情或直接导出结果。'
  if (task.status === 'partial_failed') return '存在失败文件，建议优先重试失败项。'
  if (task.status === 'failed') return '执行异常终止，建议查看详情后重试。'
  if (task.status === 'running') return '任务仍在执行，页面会持续展示最新状态。'
  return '任务已进入队列，等待开始处理。'
}

const taskMeta = (task: InferenceTaskResponse) => {
  return [`${task.file_count} 张图片`, `进度 ${task.progress}%`, formatTime(task.created_at)]
}
</script>

<style scoped>
.task-history {
  height: 100%;
  padding: 20px;
}

.status-filter {
  width: 120px;
}

.action-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.task-history :deep(.workspace-action) {
  min-height: 32px;
}

.inline-button,
.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-chip {
  border: 1px solid transparent;
}

.status-pending {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.status-running,
.status-partial_failed {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.status-completed {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.status-failed {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.inline-button {
  border: 0;
  background: rgba(29, 78, 216, 0.08);
  color: var(--brand);
  cursor: pointer;
}

.inline-button.success {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.inline-button.danger {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.inline-button.subtle {
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
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
  color: #0f766e;
  font-size: 22px;
}
</style>

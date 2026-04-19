<template>
  <el-card class="task-history-card">
    <template #header>
      <div class="card-header">
        <span>最近任务</span>
        <div class="header-actions">
          <el-select
            :model-value="statusFilter"
            placeholder="筛选状态"
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
          <el-button text @click="emit('refresh')">刷新</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!tasks.length" description="暂无批量任务" />

    <el-table v-else :data="tasks" stripe>
      <el-table-column label="任务 ID" min-width="180">
        <template #default="scope">
          <el-button link type="primary" @click="emit('select', scope.row.task_id)">
            {{ scope.row.task_id }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="scope">
          <el-tag :type="statusType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_count" label="图片数" width="80" />
      <el-table-column prop="progress" label="进度" width="80" />
      <el-table-column label="创建时间" min-width="160">
        <template #default="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="140">
        <template #default="scope">
          <div class="row-actions">
            <el-button link type="primary" @click="emit('select', scope.row.task_id)"
              >查看</el-button
            >
            <el-button
              v-if="scope.row.status === 'failed'"
              link
              type="danger"
              @click="emit('retry', scope.row.task_id)"
            >
              重试
            </el-button>
            <el-button
              v-else-if="scope.row.status === 'completed'"
              link
              type="success"
              @click="emit('rerun', scope.row.task_id)"
            >
              复跑
            </el-button>
            <el-button
              v-if="scope.row.status === 'completed'"
              link
              type="primary"
              @click="emit('export', scope.row.task_id)"
            >
              导出
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import {
  ElButton,
  ElCard,
  ElEmpty,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import type { InferenceTaskResponse, InferenceTaskStatus } from '@/types/api'

defineProps<{
  tasks: InferenceTaskResponse[]
  statusFilter: InferenceTaskStatus | ''
}>()

const emit = defineEmits<{
  refresh: []
  select: [taskId: string]
  retry: [taskId: string]
  rerun: [taskId: string]
  export: [taskId: string]
  'update:statusFilter': [status: InferenceTaskStatus | '']
}>()

const handleStatusChange = (value: InferenceTaskStatus | '' | undefined) => {
  emit('update:statusFilter', value ?? '')
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

const statusText = (status: string): string => {
  switch (status) {
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '待开始'
  }
}

const statusType = (status: string): 'info' | 'warning' | 'success' | 'danger' => {
  switch (status) {
    case 'running':
      return 'warning'
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}
</script>

<style scoped>
.task-history-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-filter {
  width: 120px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

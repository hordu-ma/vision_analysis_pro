<template>
  <el-drawer :model-value="visible" size="55%" title="任务详情" @close="emit('close')">
    <div v-if="task" class="detail-wrapper">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务 ID">{{ task.task_id }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">{{ task.status }}</el-descriptions-item>
        <el-descriptions-item label="文件数量">{{ task.file_count }}</el-descriptions-item>
        <el-descriptions-item label="已完成">{{ task.completed_files }}</el-descriptions-item>
        <el-descriptions-item label="失败文件">
          {{ task.metadata.failed_files ?? 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="总耗时">
          {{ task.metadata.batch_inference_time_ms ?? 0 }} ms
        </el-descriptions-item>
      </el-descriptions>

      <div class="detail-actions">
        <el-button type="primary" plain @click="emit('export-csv', task.task_id)">
          导出 CSV
        </el-button>
        <el-button type="success" plain @click="emit('export-json', task.task_id)">
          导出 JSON
        </el-button>
        <el-button type="warning" plain @click="emit('export-zip', task.task_id)">
          导出 ZIP
        </el-button>
        <el-button
          v-if="task.status === 'partial_failed'"
          type="danger"
          plain
          @click="emit('retry-failed', task.task_id)"
        >
          重试失败文件
        </el-button>
      </div>

      <el-table :data="task.files" stripe>
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="检测数" width="100">
          <template #default="scope">
            {{ scope.row.result?.detections.length ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="220">
          <template #default="scope">
            {{ scope.row.error?.message || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-empty v-else description="请选择任务查看详情" />
  </el-drawer>
</template>

<script setup lang="ts">
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElEmpty,
  ElTable,
  ElTableColumn
} from 'element-plus'
import type { InferenceTaskDetailResponse } from '@/types/api'

defineProps<{
  visible: boolean
  task: InferenceTaskDetailResponse | null
}>()

const emit = defineEmits<{
  close: []
  'retry-failed': [taskId: string]
  'export-csv': [taskId: string]
  'export-json': [taskId: string]
  'export-zip': [taskId: string]
}>()
</script>

<style scoped>
.detail-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>

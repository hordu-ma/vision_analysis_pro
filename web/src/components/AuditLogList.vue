<template>
  <el-card class="audit-log-card">
    <template #header>
      <div class="card-header">
        <span>审计日志</span>
        <div class="header-actions">
          <el-input
            :model-value="actorFilter"
            placeholder="按操作者筛选"
            size="small"
            class="actor-filter"
            @input="emit('update:actorFilter', String($event))"
          />
          <el-button text @click="emit('refresh')">刷新</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!logs.length" description="暂无审计记录" />

    <el-table v-else :data="logs" stripe>
      <el-table-column prop="event_type" label="事件" min-width="140" />
      <el-table-column prop="resource_id" label="资源" min-width="140" />
      <el-table-column prop="actor" label="操作者" width="100" />
      <el-table-column label="时间" min-width="160">
        <template #default="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="detail_json" label="详情" min-width="220" show-overflow-tooltip />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElEmpty, ElInput, ElTable, ElTableColumn } from 'element-plus'
import type { AuditLogResponse } from '@/types/api'

defineProps<{
  logs: AuditLogResponse[]
  actorFilter: string
}>()

const emit = defineEmits<{
  refresh: []
  'update:actorFilter': [actor: string]
}>()

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}
</script>

<style scoped>
.audit-log-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.actor-filter {
  width: 160px;
}
</style>

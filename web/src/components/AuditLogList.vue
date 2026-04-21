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

    <div v-if="!logs.length" class="empty-state">
      <div class="empty-icon">◌</div>
      <p>暂无审计记录</p>
    </div>

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

    <div class="pagination-bar" data-testid="audit-pagination">
      <span>{{ pageSummary }}</span>
      <div class="pagination-actions">
        <el-button size="small" :disabled="!canPrevious" @click="emitPage(offset - limit)">
          上一页
        </el-button>
        <el-button size="small" :disabled="!canNext" @click="emitPage(offset + limit)">
          下一页
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ElButton, ElCard, ElInput, ElTable, ElTableColumn } from 'element-plus'
import { computed } from 'vue'
import type { AuditLogResponse } from '@/types/api'

const props = withDefaults(
  defineProps<{
    logs: AuditLogResponse[]
    actorFilter: string
    total?: number
    limit?: number
    offset?: number
  }>(),
  {
    total: 0,
    limit: 20,
    offset: 0
  }
)

const emit = defineEmits<{
  refresh: []
  page: [offset: number]
  'update:actorFilter': [actor: string]
}>()

const offset = computed(() => props.offset)
const limit = computed(() => props.limit)
const canPrevious = computed(() => props.offset > 0)
const canNext = computed(() => props.offset + props.logs.length < props.total)
const pageSummary = computed(() => {
  if (props.total === 0) return '0 / 0'
  return `${props.offset + 1}-${props.offset + props.logs.length} / ${props.total}`
})

const emitPage = (nextOffset: number) => {
  if (nextOffset < 0 || nextOffset === props.offset) return
  emit('page', nextOffset)
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}
</script>

<style scoped>
.audit-log-card {
  margin-bottom: 0;
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

.audit-log-card :deep(.el-card__header) {
  padding-bottom: 14px;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-soft);
  color: var(--text-muted);
  font-size: 12px;
}

.pagination-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.empty-state {
  min-height: 220px;
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

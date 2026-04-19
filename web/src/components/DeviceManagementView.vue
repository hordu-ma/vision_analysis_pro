<template>
  <div class="device-management-view">
    <section class="device-overview-bar">
      <div class="overview-copy">
        <p class="overview-kicker">Device Control</p>
        <h3>设备概览、告警摘要、审计记录</h3>
        <p>首屏聚焦设备运维主流程。</p>
      </div>
      <div class="overview-stats">
        <div class="overview-stat">
          <span>设备数量</span>
          <strong>{{ devices.length }}</strong>
        </div>
        <div class="overview-stat">
          <span>审计记录</span>
          <strong>{{ logs.length }}</strong>
        </div>
        <div class="overview-stat subtle">
          <span>当前筛选</span>
          <strong>{{ actorFilter || '全部操作者' }}</strong>
        </div>
      </div>
    </section>

    <el-row :gutter="20" class="device-main-grid">
      <el-col :lg="16" :xs="24">
        <DeviceOverview
          :devices="devices"
          @refresh="emit('refresh-devices')"
          @select-device="emit('select-device', $event)"
          @edit-device="emit('edit-device', $event)"
        />
      </el-col>
      <el-col :lg="8" :xs="24">
        <AlertSummaryCard :summary="summary" @refresh="emit('refresh-alerts')" />
      </el-col>
    </el-row>

    <section class="audit-section">
      <AuditLogList
        :logs="logs"
        :actor-filter="actorFilter"
        @refresh="emit('refresh-audit-logs')"
        @update:actor-filter="emit('update:actor-filter', $event)"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElCol, ElRow } from 'element-plus'
import AlertSummaryCard from '@/components/AlertSummaryCard.vue'
import AuditLogList from '@/components/AuditLogList.vue'
import DeviceOverview from '@/components/DeviceOverview.vue'
import type { AlertSummaryResponse, AuditLogResponse, ReportDeviceSummary } from '@/types/api'

defineProps<{
  summary: AlertSummaryResponse | null
  devices: ReportDeviceSummary[]
  logs: AuditLogResponse[]
  actorFilter: string
}>()

const emit = defineEmits<{
  'refresh-alerts': []
  'refresh-devices': []
  'refresh-audit-logs': []
  'select-device': [deviceId: string]
  'edit-device': [deviceId: string]
  'update:actor-filter': [actor: string]
}>()
</script>

<style scoped>
.device-management-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.device-overview-bar {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.9fr);
  gap: 18px;
  padding: 4px 0 0;
}

.overview-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--brand);
  font-weight: 700;
}

.overview-copy h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  white-space: nowrap;
}

.overview-copy p:last-child {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-self: center;
}

.overview-stat {
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
}

.overview-stat.subtle {
  background: rgba(29, 78, 216, 0.06);
}

.overview-stat span,
.overview-stat strong {
  display: block;
}

.overview-stat span {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.overview-stat strong {
  font-size: 16px;
  white-space: nowrap;
}

.device-main-grid,
.audit-section {
  margin-top: 2px;
}

@media (max-width: 960px) {
  .device-overview-bar {
    grid-template-columns: 1fr;
  }

  .overview-stats {
    grid-template-columns: 1fr;
  }
}
</style>

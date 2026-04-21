<template>
  <div class="device-management-view">
    <section class="device-overview-bar">
      <div class="overview-copy">
        <p class="overview-kicker">Device Control</p>
        <h3>设备概览与审计留痕</h3>
        <p>统一查看设备状态、告警摘要和操作记录。</p>
      </div>
      <div class="device-signal" aria-label="设备链路状态">
        <span class="signal-node active">Edge</span>
        <i></i>
        <span class="signal-node">API</span>
        <i></i>
        <span class="signal-node">Review</span>
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
          :total="deviceTotal"
          :limit="deviceLimit"
          :offset="deviceOffset"
          @refresh="emit('refresh-devices')"
          @page="emit('page-devices', $event)"
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
        :total="auditLogTotal"
        :limit="auditLogLimit"
        :offset="auditLogOffset"
        @refresh="emit('refresh-audit-logs')"
        @page="emit('page-audit-logs', $event)"
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
  deviceTotal: number
  deviceLimit: number
  deviceOffset: number
  logs: AuditLogResponse[]
  auditLogTotal: number
  auditLogLimit: number
  auditLogOffset: number
  actorFilter: string
}>()

const emit = defineEmits<{
  'refresh-alerts': []
  'refresh-devices': []
  'page-devices': [offset: number]
  'refresh-audit-logs': []
  'page-audit-logs': [offset: number]
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
  grid-template-columns: minmax(0, 0.9fr) minmax(320px, 0.7fr) minmax(280px, 0.9fr);
  gap: 16px;
  align-items: stretch;
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
  font-size: 22px;
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

.device-signal {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(15, 23, 42, 0.04));
  border: 1px solid var(--border-soft);
}

.signal-node {
  min-height: 28px;
  display: inline-grid;
  place-items: center;
  padding: 0 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.signal-node.active {
  color: #fff;
  background: var(--brand);
}

.device-signal i {
  height: 2px;
  min-width: 28px;
  background: linear-gradient(90deg, rgba(15, 118, 110, 0.45), rgba(15, 23, 42, 0.18));
}

.overview-stat {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
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

  .device-signal {
    grid-template-columns: 1fr;
  }

  .device-signal i {
    width: 2px;
    height: 12px;
    min-width: 0;
    justify-self: center;
  }

  .overview-stats {
    grid-template-columns: 1fr;
  }
}
</style>

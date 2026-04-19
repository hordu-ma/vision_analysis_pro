<template>
  <div class="device-management-view">
    <AlertSummaryCard :summary="summary" @refresh="emit('refresh-alerts')" />
    <DeviceOverview
      :devices="devices"
      @refresh="emit('refresh-devices')"
      @select-device="emit('select-device', $event)"
      @edit-device="emit('edit-device', $event)"
    />
    <AuditLogList
      :logs="logs"
      :actor-filter="actorFilter"
      @refresh="emit('refresh-audit-logs')"
      @update:actor-filter="emit('update:actor-filter', $event)"
    />
  </div>
</template>

<script setup lang="ts">
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
  gap: 24px;
}
</style>

<template>
  <DeviceManagementView
    :summary="summary"
    :devices="devices"
    :logs="logs"
    :actor-filter="actorFilter"
    @refresh-alerts="emit('refresh-alerts')"
    @refresh-devices="emit('refresh-devices')"
    @refresh-audit-logs="emit('refresh-audit-logs')"
    @select-device="emit('select-device', $event)"
    @edit-device="emit('edit-device', $event)"
  />
</template>

<script setup lang="ts">
import DeviceManagementView from '@/components/DeviceManagementView.vue'
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

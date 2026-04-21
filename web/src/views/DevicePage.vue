<template>
  <DeviceManagementView
    :summary="summary"
    :devices="devices"
    :device-total="deviceTotal"
    :device-limit="deviceLimit"
    :device-offset="deviceOffset"
    :logs="logs"
    :actor-filter="actorFilter"
    @refresh-alerts="emit('refresh-alerts')"
    @refresh-devices="emit('refresh-devices')"
    @page-devices="emit('page-devices', $event)"
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
  deviceTotal: number
  deviceLimit: number
  deviceOffset: number
  logs: AuditLogResponse[]
  actorFilter: string
}>()

const emit = defineEmits<{
  'refresh-alerts': []
  'refresh-devices': []
  'page-devices': [offset: number]
  'refresh-audit-logs': []
  'select-device': [deviceId: string]
  'edit-device': [deviceId: string]
  'update:actor-filter': [actor: string]
}>()
</script>

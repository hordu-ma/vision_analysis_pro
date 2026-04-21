<template>
  <DeviceManagementView
    :summary="summary"
    :devices="devices"
    :device-total="deviceTotal"
    :device-limit="deviceLimit"
    :device-offset="deviceOffset"
    :logs="logs"
    :audit-log-total="auditLogTotal"
    :audit-log-limit="auditLogLimit"
    :audit-log-offset="auditLogOffset"
    :actor-filter="actorFilter"
    @refresh-alerts="emit('refresh-alerts')"
    @refresh-devices="emit('refresh-devices')"
    @page-devices="emit('page-devices', $event)"
    @refresh-audit-logs="emit('refresh-audit-logs')"
    @page-audit-logs="emit('page-audit-logs', $event)"
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

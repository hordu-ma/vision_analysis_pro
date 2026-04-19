<template>
  <el-drawer :model-value="visible" title="设备设置" size="420px" @close="emit('close')">
    <el-form :model="form" label-width="88px">
      <el-form-item label="设备 ID">
        <el-input :model-value="deviceId" disabled />
      </el-form-item>
      <el-form-item label="显示名称">
        <el-input v-model="form.display_name" />
      </el-form-item>
      <el-form-item label="站点">
        <el-input v-model="form.site_name" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" :rows="4" />
      </el-form-item>
      <el-button type="primary" @click="emit('save', form)">保存</el-button>
    </el-form>
  </el-drawer>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { ElButton, ElDrawer, ElForm, ElFormItem, ElInput } from 'element-plus'
import type { ReportDeviceMetadataRequest, ReportDeviceSummary } from '@/types/api'

const props = defineProps<{
  visible: boolean
  deviceId: string
  device: ReportDeviceSummary | null
}>()

const emit = defineEmits<{
  close: []
  save: [payload: ReportDeviceMetadataRequest]
}>()

const form = reactive<ReportDeviceMetadataRequest>({
  site_name: '',
  display_name: '',
  note: ''
})

watch(
  () => props.device,
  device => {
    form.site_name = device?.site_name || ''
    form.display_name = device?.display_name || ''
    form.note = device?.note || ''
  },
  { immediate: true }
)
</script>

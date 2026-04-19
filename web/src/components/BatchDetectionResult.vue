<template>
  <div v-if="result" class="batch-detection-result">
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <span>批量分析结果</span>
          <el-button
            v-if="taskId"
            type="primary"
            plain
            size="small"
            @click="emit('export', taskId)"
          >
            导出 CSV
          </el-button>
          <el-button v-if="taskId" type="info" plain size="small" @click="emit('detail', taskId)">
            查看详情
          </el-button>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-statistic title="图片数量" :value="result.files.length" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="检测总数" :value="totalDetections" />
        </el-col>
        <el-col :span="8">
          <el-statistic
            title="总耗时"
            :value="result.metadata.batch_inference_time_ms || 0"
            :precision="1"
            suffix="ms"
          />
        </el-col>
      </el-row>
    </el-card>

    <el-card class="details-card">
      <template #header>
        <div class="card-header">
          <span>逐图结果</span>
        </div>
      </template>
      <el-collapse accordion>
        <el-collapse-item
          v-for="file in result.files"
          :key="file.filename"
          :title="`${file.filename} · ${file.detections.length} 个检测`"
          :name="file.filename"
        >
          <DetectionResult :result="file" />
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {
  ElButton,
  ElCard,
  ElCol,
  ElCollapse,
  ElCollapseItem,
  ElRow,
  ElStatistic
} from 'element-plus'
import { computed } from 'vue'
import DetectionResult from '@/components/DetectionResult.vue'
import type { BatchInferenceResponse } from '@/types/api'

const props = defineProps<{
  result: BatchInferenceResponse | null
  taskId?: string
}>()

const emit = defineEmits<{
  export: [taskId: string]
  detail: [taskId: string]
}>()

const totalDetections = computed(() => {
  if (!props.result) return 0
  return props.result.files.reduce((sum, item) => sum + item.detections.length, 0)
})
</script>

<style scoped>
.batch-detection-result {
  margin-top: 20px;
}

.stats-card,
.details-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>

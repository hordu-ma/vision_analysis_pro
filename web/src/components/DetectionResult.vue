<template>
  <div v-if="result" class="detection-result">
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <span>检测统计</span>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-statistic title="检测数量" :value="result.detections.length" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="平均置信度" :value="avgConfidence" :precision="2" suffix="%" />
        </el-col>
        <el-col :span="8">
          <el-statistic
            v-if="result.metadata.inference_time_ms"
            title="推理时间"
            :value="result.metadata.inference_time_ms"
            :precision="1"
            suffix="ms"
          />
        </el-col>
      </el-row>
    </el-card>

    <el-card v-if="result.visualization" class="visualization-card">
      <template #header>
        <div class="card-header">
          <span>可视化结果</span>
        </div>
      </template>
      <el-image :src="result.visualization" fit="contain" class="visualization-image" />
    </el-card>

    <el-card class="details-card">
      <template #header>
        <div class="card-header">
          <span>检测详情</span>
        </div>
      </template>
      <el-table :data="result.detections" stripe style="width: 100%">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="label" label="类别" width="150">
          <template #default="{ row }">
            <el-tag>{{ row.label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="120">
          <template #default="{ row }"> {{ (row.confidence * 100).toFixed(2) }}% </template>
        </el-table-column>
        <el-table-column prop="bbox" label="边界框 [x1, y1, x2, y2]">
          <template #default="{ row }">
            {{ row.bbox.map((v: number) => v.toFixed(1)).join(', ') }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>

  <el-empty v-else description="暂无检测结果" />
</template>

<script setup lang="ts">
import {
  ElCard,
  ElCol,
  ElEmpty,
  ElImage,
  ElRow,
  ElStatistic,
  ElTable,
  ElTableColumn,
  ElTag
} from 'element-plus'
import { computed } from 'vue'
import type { InferenceResponse } from '@/types/api'

const props = defineProps<{
  result: InferenceResponse | null
}>()

const avgConfidence = computed(() => {
  if (!props.result || props.result.detections.length === 0) return 0
  const sum = props.result.detections.reduce((acc: number, det) => acc + det.confidence, 0)
  return (sum / props.result.detections.length) * 100
})
</script>

<style scoped>
.detection-result {
  margin-top: 20px;
}

.stats-card,
.visualization-card,
.details-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.visualization-image {
  width: 100%;
  max-height: 600px;
}
</style>

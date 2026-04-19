<template>
  <el-drawer :model-value="visible" size="55%" title="批次详情" @close="emit('close')">
    <div v-if="report" class="detail-wrapper">
      <div class="detail-hero">
        <div>
          <p class="detail-kicker">Batch Archive</p>
          <h3>{{ report.batch_id }}</h3>
          <p>用于查看边缘上报批次、人工复核与导出交付明细。</p>
        </div>
        <span class="detail-status">{{ report.device_id }}</span>
      </div>

      <el-descriptions :column="2" border class="detail-summary">
        <el-descriptions-item label="批次 ID">{{ report.batch_id }}</el-descriptions-item>
        <el-descriptions-item label="设备 ID">{{ report.device_id }}</el-descriptions-item>
        <el-descriptions-item label="结果数">{{ report.result_count }}</el-descriptions-item>
        <el-descriptions-item label="检测数">{{ report.total_detections }}</el-descriptions-item>
        <el-descriptions-item label="上报时间">
          {{ formatTime(report.report_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="接收时间">
          {{ formatTime(report.created_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="detail-actions">
        <el-button type="primary" plain @click="emit('export', report.batch_id)">
          导出 CSV
        </el-button>
      </div>

      <el-collapse accordion>
        <el-collapse-item
          v-for="item in report.results"
          :key="item.frame_id"
          :title="`帧 ${item.frame_id} · ${formatReviewStatus(item.review?.status)}`"
          :name="item.frame_id"
        >
          <div class="frame-header">
            <div><strong>图片：</strong>{{ imageName(item) }}</div>
            <div><strong>推理耗时：</strong>{{ item.inference_time_ms.toFixed(1) }} ms</div>
          </div>

          <el-table :data="item.detections" stripe size="small" class="detail-table">
            <el-table-column prop="label" label="缺陷类别" min-width="120" />
            <el-table-column label="置信度" width="100">
              <template #default="scope"> {{ (scope.row.confidence * 100).toFixed(1) }}% </template>
            </el-table-column>
            <el-table-column label="边界框" min-width="220">
              <template #default="scope">
                {{ scope.row.bbox.join(', ') }}
              </template>
            </el-table-column>
          </el-table>

          <el-form label-width="88px" class="review-form">
            <el-form-item label="复核状态">
              <el-select
                :model-value="
                  reviewDrafts[item.frame_id]?.status ?? item.review?.status ?? 'pending'
                "
                placeholder="选择状态"
                @update:model-value="value => updateDraft(item.frame_id, 'status', value)"
              >
                <el-option label="待处理" value="pending" />
                <el-option label="确认问题" value="confirmed" />
                <el-option label="误报" value="false_positive" />
                <el-option label="忽略" value="ignored" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核人">
              <el-input
                :model-value="reviewDrafts[item.frame_id]?.reviewer ?? item.review?.reviewer ?? ''"
                placeholder="填写复核人"
                @update:model-value="value => updateDraft(item.frame_id, 'reviewer', value)"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                type="textarea"
                :rows="2"
                :model-value="reviewDrafts[item.frame_id]?.note ?? item.review?.note ?? ''"
                placeholder="填写备注"
                @update:model-value="value => updateDraft(item.frame_id, 'note', value)"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="emit('save-review', item.frame_id, reviewPayload(item))"
              >
                保存复核
              </el-button>
              <span v-if="item.review" class="review-meta">
                最近更新：{{ item.review.reviewer || '未填写' }} /
                {{ formatTime(item.review.updated_at) }}
              </span>
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
    </div>
    <el-empty v-else description="请选择批次查看详情" />
  </el-drawer>
</template>

<script setup lang="ts">
import {
  ElButton,
  ElCollapse,
  ElCollapseItem,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn
} from 'element-plus'
import { reactive, watch } from 'vue'
import type {
  ReportFrameResult,
  ReportRecordResponse,
  ReportReviewRequest,
  ReviewStatus
} from '@/types/api'

const props = defineProps<{
  visible: boolean
  report: ReportRecordResponse | null
}>()

const emit = defineEmits<{
  close: []
  export: [batchId: string]
  'save-review': [frameId: number, payload: ReportReviewRequest]
}>()

const reviewDrafts = reactive<Record<number, ReportReviewRequest>>({})

watch(
  () => props.report,
  report => {
    for (const key of Object.keys(reviewDrafts)) {
      delete reviewDrafts[Number(key)]
    }
    if (!report) return
    for (const item of report.results) {
      reviewDrafts[item.frame_id] = {
        status: item.review?.status ?? 'pending',
        note: item.review?.note ?? '',
        reviewer: item.review?.reviewer ?? ''
      }
    }
  },
  { immediate: true }
)

const updateDraft = <K extends keyof ReportReviewRequest>(
  frameId: number,
  key: K,
  value: ReportReviewRequest[K]
) => {
  if (!reviewDrafts[frameId]) {
    reviewDrafts[frameId] = { status: 'pending', note: '', reviewer: '' }
  }
  reviewDrafts[frameId][key] = value
}

const reviewPayload = (item: ReportFrameResult): ReportReviewRequest => {
  return (
    reviewDrafts[item.frame_id] ?? {
      status: item.review?.status ?? 'pending',
      note: item.review?.note ?? '',
      reviewer: item.review?.reviewer ?? ''
    }
  )
}

const imageName = (item: ReportFrameResult): string => {
  return String(item.metadata.image_name ?? item.source_id ?? '-')
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

const formatReviewStatus = (status?: ReviewStatus | null): string => {
  switch (status) {
    case 'confirmed':
      return '确认问题'
    case 'false_positive':
      return '误报'
    case 'ignored':
      return '忽略'
    default:
      return '待处理'
  }
}
</script>

<style scoped>
.detail-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.95), rgba(15, 23, 42, 0.92));
  color: rgba(255, 255, 255, 0.94);
}

.detail-kicker {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(165, 243, 252, 0.82);
}

.detail-hero h3 {
  margin: 0;
  font-size: 26px;
}

.detail-hero p:last-child {
  margin: 8px 0 0;
  color: rgba(224, 242, 254, 0.78);
}

.detail-status {
  align-self: flex-start;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
}

.frame-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: #606266;
}

.detail-table {
  margin-bottom: 16px;
}

.review-form {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.review-meta {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}

@media (max-width: 768px) {
  .frame-header {
    flex-direction: column;
  }
}
</style>

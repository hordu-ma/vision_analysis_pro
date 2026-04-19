<template>
  <div v-if="result" class="detection-result" data-testid="detection-result">
    <section class="result-hero product-shell-card">
      <div class="hero-copy">
        <p class="hero-kicker">Single Image Review</p>
        <h3>{{ result.filename }}</h3>
        <p class="hero-summary">{{ summaryText }}</p>
      </div>
      <div class="hero-metrics">
        <div class="metric-chip">
          <span>缺陷项</span>
          <strong>{{ result.detections.length }}</strong>
        </div>
        <div class="metric-chip">
          <span>最高风险</span>
          <strong>{{ topRiskLabel }}</strong>
        </div>
        <div v-if="result.metadata.inference_time_ms" class="metric-chip">
          <span>推理耗时</span>
          <strong>{{ formatInferenceTime(result.metadata.inference_time_ms) }} ms</strong>
        </div>
      </div>
    </section>

    <section class="result-overview">
      <div class="overview-panel product-shell-card">
        <div class="panel-heading">
          <div>
            <p class="panel-title">检测统计</p>
            <p class="panel-caption">聚焦客户最关心的缺陷数量、可信度和处置优先级。</p>
          </div>
        </div>
        <div class="overview-grid">
          <article class="overview-card" data-testid="detection-count">
            <span>检测数量</span>
            <strong>{{ result.detections.length }}</strong>
          </article>
          <article class="overview-card">
            <span>平均置信度</span>
            <strong>{{ avgConfidence.toFixed(1) }}%</strong>
          </article>
          <article class="overview-card">
            <span>建议动作</span>
            <strong>{{ nextActionLabel }}</strong>
          </article>
        </div>
      </div>

      <div v-if="topDetection" class="overview-panel product-shell-card">
        <div class="panel-heading">
          <div>
            <p class="panel-title">首要缺陷</p>
            <p class="panel-caption">默认突出最值得人工复核的一项，避免信息平铺。</p>
          </div>
        </div>
        <article class="priority-card" :class="`risk-${topRisk.level}`">
          <div>
            <p class="priority-label">{{ defectMeta(topDetection.label).name }}</p>
            <h4>{{ topRiskLabel }}</h4>
            <p>{{ defectMeta(topDetection.label).description }}</p>
          </div>
          <div class="priority-stats">
            <span>置信度 {{ formatConfidence(topDetection.confidence) }}</span>
            <span>{{ bboxText(topDetection.bbox) }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-if="result.visualization" class="visual-panel product-shell-card">
      <div class="panel-heading">
        <div>
          <p class="panel-title">可视化结果</p>
          <p class="panel-caption">保留边框标注图，便于演示识别区域与人工复核。</p>
        </div>
      </div>
      <el-image :src="result.visualization" fit="contain" class="visualization-image" />
    </section>

    <section class="detail-panel product-shell-card">
      <div class="panel-heading">
        <div>
          <p class="panel-title">缺陷详情</p>
          <p class="panel-caption">改为记录式列表，强调缺陷语义与建议动作，不再像后台表格。</p>
        </div>
      </div>

      <div v-if="result.detections.length" class="detail-list">
        <article
          v-for="(detection, index) in result.detections"
          :key="`${detection.label}-${index}`"
          class="detail-item"
          :class="`risk-${riskForDetection(detection).level}`"
        >
          <div class="detail-main">
            <div class="detail-index">{{ index + 1 }}</div>
            <div>
              <div class="detail-title-row">
                <h4>{{ defectMeta(detection.label).name }}</h4>
                <span class="risk-badge">{{ riskForDetection(detection).label }}</span>
              </div>
              <p class="detail-description">{{ defectMeta(detection.label).description }}</p>
            </div>
          </div>
          <div class="detail-meta">
            <span>置信度 {{ formatConfidence(detection.confidence) }}</span>
            <span>{{ bboxText(detection.bbox) }}</span>
            <span>{{ defectMeta(detection.label).action }}</span>
          </div>
        </article>
      </div>

      <div v-else class="empty-inline-state">
        <div class="empty-inline-icon">○</div>
        <div>
          <p>当前图片未识别到缺陷</p>
          <span>可继续上传更接近巡检场景的图片，或降低阈值做人工复核演示。</span>
        </div>
      </div>
    </section>
  </div>

  <div v-else class="empty-state">
    <div class="empty-icon">◔</div>
    <p>暂无检测结果</p>
  </div>
</template>

<script setup lang="ts">
import { ElImage } from 'element-plus'
import { computed } from 'vue'
import type { DetectionBox, InferenceResponse } from '@/types/api'

const props = defineProps<{
  result: InferenceResponse | null
}>()

type RiskLevel = 'high' | 'medium' | 'low'

const defectCatalog: Record<
  string,
  { name: string; description: string; action: string; defaultRisk: RiskLevel }
> = {
  crack: {
    name: '裂缝',
    description: '结构表面疑似存在开裂特征，建议优先复核裂缝长度和扩展趋势。',
    action: '建议现场复查并记录裂缝尺度',
    defaultRisk: 'high'
  },
  rust: {
    name: '锈蚀',
    description: '金属部位存在明显锈蚀迹象，可能影响表面防护和长期耐久性。',
    action: '建议安排除锈与防腐补涂',
    defaultRisk: 'medium'
  },
  deformation: {
    name: '变形',
    description: '构件轮廓出现疑似弯折或偏移，需确认是否影响结构受力。',
    action: '建议复测形变量并评估结构安全',
    defaultRisk: 'high'
  },
  spalling: {
    name: '剥落',
    description: '混凝土或保护层表面存在剥落迹象，需关注暴露区域扩大风险。',
    action: '建议核查剥落面积并安排修补',
    defaultRisk: 'medium'
  },
  corrosion: {
    name: '腐蚀',
    description: '表面存在腐蚀痕迹，可能伴随保护层失效或局部材质退化。',
    action: '建议结合环境条件进行腐蚀等级评估',
    defaultRisk: 'medium'
  }
}

const avgConfidence = computed(() => {
  if (!props.result || props.result.detections.length === 0) return 0
  const sum = props.result.detections.reduce((acc: number, det) => acc + det.confidence, 0)
  return (sum / props.result.detections.length) * 100
})

const sortedDetections = computed(() => {
  return [...(props.result?.detections ?? [])].sort((a, b) => b.confidence - a.confidence)
})

const topDetection = computed(() => sortedDetections.value[0] ?? null)

const defectMeta = (label: string) => {
  return (
    defectCatalog[label] ?? {
      name: label,
      description: '当前类别暂无预设说明，建议人工复核具体缺陷表现。',
      action: '建议人工复核',
      defaultRisk: 'low' as RiskLevel
    }
  )
}

const riskForDetection = (detection: DetectionBox) => {
  const preset = defectMeta(detection.label)
  if (detection.confidence >= 0.9) {
    return { level: 'high' as RiskLevel, label: '高优先级' }
  }
  if (detection.confidence >= 0.75) {
    return {
      level: preset.defaultRisk === 'low' ? 'medium' : preset.defaultRisk,
      label: preset.defaultRisk === 'high' ? '高优先级' : '建议复核'
    }
  }
  return { level: 'low' as RiskLevel, label: '观察项' }
}

const topRisk = computed(() => {
  if (!topDetection.value) {
    return { level: 'low' as RiskLevel, label: '未发现异常' }
  }
  return riskForDetection(topDetection.value)
})

const topRiskLabel = computed(() => topRisk.value.label)

const nextActionLabel = computed(() => {
  if (!topDetection.value) return '继续抽检'
  return defectMeta(topDetection.value.label).action
})

const summaryText = computed(() => {
  if (!props.result) return ''
  if (props.result.detections.length === 0) {
    return '当前图片未发现明确缺陷，可作为巡检通过样本留档。'
  }
  const top = topDetection.value
  if (!top) return '已完成图像分析。'
  return `本次识别以${defectMeta(top.label).name}为主，建议围绕该区域进行人工复核与处置判断。`
})

const formatConfidence = (confidence: number) => `${(confidence * 100).toFixed(1)}%`

const formatInferenceTime = (value: number) => {
  return (Math.floor(value * 10) / 10).toFixed(1)
}

const bboxText = (bbox: [number, number, number, number]) => {
  return `框选 ${bbox.map(v => v.toFixed(0)).join(' / ')}`
}
</script>

<style scoped>
.detection-result {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-hero,
.overview-panel,
.visual-panel,
.detail-panel {
  padding: 22px;
}

.result-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.9fr);
  gap: 18px;
}

.hero-kicker,
.panel-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
}

.hero-kicker {
  margin-bottom: 8px;
  color: var(--brand);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 11px;
}

.hero-copy h3 {
  margin: 0;
  font-size: 24px;
  line-height: 1.18;
}

.hero-summary,
.panel-caption,
.detail-description,
.empty-inline-state span {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.hero-metrics {
  display: grid;
  gap: 10px;
}

.metric-chip,
.overview-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.78);
  border: 1px solid var(--border-soft);
}

.metric-chip span,
.metric-chip strong,
.overview-card span,
.overview-card strong {
  display: block;
}

.metric-chip span,
.overview-card span {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.metric-chip strong,
.overview-card strong {
  font-size: 18px;
  line-height: 1.25;
}

.result-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 16px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.priority-card,
.detail-item {
  border-radius: 18px;
  border: 1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.86));
}

.priority-card {
  padding: 18px;
}

.priority-label {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.priority-card h4 {
  margin: 0;
  font-size: 22px;
}

.priority-card p {
  margin: 10px 0 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.priority-stats,
.detail-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.priority-stats span,
.detail-meta span,
.risk-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--text-secondary);
  font-size: 12px;
}

.visualization-image {
  width: 100%;
  max-height: 560px;
  border-radius: 18px;
  background: #f8fafc;
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  padding: 16px 18px;
}

.detail-main {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.detail-index {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.05);
  color: var(--text-primary);
  font-weight: 700;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-title-row h4 {
  margin: 0;
  font-size: 17px;
}

.risk-high {
  border-color: rgba(239, 68, 68, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(254, 242, 242, 0.88));
}

.risk-medium {
  border-color: rgba(245, 158, 11, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 251, 235, 0.88));
}

.risk-low {
  border-color: rgba(59, 130, 246, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.82));
}

.empty-inline-state,
.empty-state {
  display: grid;
  place-items: center;
  gap: 12px;
  color: var(--text-muted);
  text-align: center;
}

.empty-inline-state {
  min-height: 180px;
  border-radius: 18px;
  background: var(--surface-muted);
  border: 1px dashed var(--border-strong);
}

.empty-inline-icon,
.empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-soft);
  font-size: 24px;
}

.empty-inline-icon {
  background: rgba(255, 255, 255, 0.9);
  color: var(--brand);
}

.empty-state {
  min-height: 220px;
  margin-top: 20px;
  border-radius: 18px;
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
}

.empty-icon {
  background: #fff;
  color: var(--brand);
}

@media (max-width: 1080px) {
  .result-hero,
  .result-overview {
    grid-template-columns: 1fr;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>

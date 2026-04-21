<template>
  <div class="image-upload product-shell-card upload-shell">
    <div class="section-heading">
      <div>
        <p class="section-title">检测发起</p>
        <p class="section-caption">支持单图检测与批量任务发起。</p>
      </div>
      <span class="data-pill">{{
        uploadMode === 'single' ? '单图' : `批量 ${selectedFiles.length}`
      }}</span>
    </div>

    <div data-testid="upload-area">
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :limit="uploadMode === 'single' ? 1 : 20"
        :multiple="uploadMode === 'batch'"
        :accept="acceptedFormats"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :file-list="fileList"
        :disabled="analyzing"
      >
        <div class="upload-visual">
          <ProductIcon name="upload-panel" class="upload-icon" />
        </div>
        <div class="upload-text">
          <p>拖拽巡检图片或<em>点击选择</em></p>
          <p class="upload-hint">JPG / PNG / WEBP，单文件 10MB 以内</p>
        </div>
      </el-upload>
    </div>

    <div v-if="previewUrl" class="preview-section" data-testid="image-preview">
      <el-image :src="previewUrl" fit="contain" class="preview-image" />
      <el-button type="danger" size="small" :disabled="analyzing" @click="clearFile">
        清除
      </el-button>
    </div>

    <div v-if="uploadMode === 'batch' && batchFileNames.length" class="batch-preview-section">
      <el-tag v-for="name in batchFileNames" :key="name" class="batch-file-tag">{{ name }}</el-tag>
    </div>

    <div class="upload-options">
      <el-radio-group v-model="uploadMode" :disabled="analyzing">
        <el-radio-button label="single">单图模式</el-radio-button>
        <el-radio-button label="batch">批量模式</el-radio-button>
      </el-radio-group>
      <el-checkbox v-model="visualize" label="生成可视化结果" :disabled="analyzing" />
    </div>

    <!-- 上传进度条 -->
    <div v-if="analyzing && uploadProgress > 0 && uploadProgress < 100" class="progress-section">
      <el-progress
        :percentage="uploadProgress"
        :stroke-width="8"
        :format="formatProgress"
        status="success"
      />
      <p class="progress-text">正在上传图片...</p>
    </div>

    <!-- 分析中状态 -->
    <div v-if="analyzing && uploadProgress >= 100" class="progress-section">
      <el-progress :percentage="100" :stroke-width="8" :indeterminate="true" status="success" />
      <p class="progress-text">
        <ProductIcon name="spinner" class="progress-icon" :spinning="true" />
        正在分析图片，请稍候...
      </p>
    </div>

    <el-button
      data-testid="analyze-button"
      type="primary"
      :loading="analyzing"
      :disabled="!selectedFile || analyzing"
      class="analyze-button"
      @click="handleAnalyze"
    >
      <template #loading>
        <ProductIcon name="spinner" class="button-loading-icon" :spinning="true" />
      </template>
      {{ analyzeButtonText }}
    </el-button>

    <!-- 错误提示卡片 -->
    <el-alert
      v-if="lastError"
      data-testid="upload-error"
      :title="lastError.message"
      type="error"
      :description="lastError.detail"
      show-icon
      closable
      class="error-alert"
      @close="clearError"
    />
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElImage,
  ElMessage,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElTag,
  ElUpload
} from 'element-plus'
import { computed, ref } from 'vue'
import type { UploadFile, UploadFiles, UploadInstance, UploadRawFile } from 'element-plus'
import ProductIcon from '@/components/ProductIcon.vue'
import { apiService, ApiError } from '@/services/api'
import type { BatchInferenceResponse, InferenceTaskResponse, InferenceResponse } from '@/types/api'

const emit = defineEmits<{
  result: [data: InferenceResponse]
  batchResult: [data: BatchInferenceResponse]
  batchTask: [data: InferenceTaskResponse]
}>()

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const selectedFiles = ref<File[]>([])
const fileList = ref<UploadFiles>([])
const previewUrl = ref<string>('')
const visualize = ref(true)
const analyzing = ref(false)
const uploadProgress = ref(0)
const lastError = ref<{ message: string; detail?: string } | null>(null)
const uploadMode = ref<'single' | 'batch'>('single')

const acceptedFormats = 'image/jpeg,image/png,image/jpg,image/webp'
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

// 计算按钮文字
const analyzeButtonText = computed(() => {
  if (!analyzing.value) return '开始分析'
  if (uploadProgress.value < 100) return '上传中...'
  return '分析中...'
})

// 格式化进度显示
const formatProgress = (percentage: number): string => {
  return `${percentage}%`
}

const batchFileNames = computed(() => selectedFiles.value.map(file => file.name))

// 清除错误
const clearError = () => {
  lastError.value = null
}

const toNativeFiles = (files: UploadFiles): File[] => {
  return files.flatMap(item => {
    const raw = item.raw as UploadRawFile | undefined
    return raw ? [raw as File] : []
  })
}

const handleFileChange = (file: UploadFile) => {
  if (!file.raw) return

  // 清除之前的错误
  clearError()

  // 验证文件大小
  if (file.raw.size > MAX_FILE_SIZE) {
    lastError.value = {
      message: '文件过大',
      detail: `文件大小 ${(file.raw.size / 1024 / 1024).toFixed(2)}MB 超过限制 10MB`
    }
    fileList.value = []
    return
  }

  // 验证文件类型
  if (!acceptedFormats.includes(file.raw.type)) {
    lastError.value = {
      message: '文件格式不支持',
      detail: `仅支持 JPG/PNG/WEBP 格式，当前文件类型: ${file.raw.type || '未知'}`
    }
    fileList.value = []
    return
  }

  if (uploadMode.value === 'single') {
    selectedFile.value = file.raw
    selectedFiles.value = [file.raw]
    previewUrl.value = URL.createObjectURL(file.raw)
  } else {
    selectedFiles.value = toNativeFiles(fileList.value)
    selectedFile.value = selectedFiles.value[0] ?? null
    previewUrl.value = selectedFile.value ? URL.createObjectURL(selectedFile.value) : ''
  }
}

const handleExceed = () => {
  if (uploadMode.value === 'single') {
    ElMessage.warning('一次只能上传一个文件，请先清除当前文件')
  } else {
    ElMessage.warning('单次最多上传 20 个文件')
  }
}

const clearFile = () => {
  selectedFile.value = null
  selectedFiles.value = []
  previewUrl.value = ''
  fileList.value = []
  uploadProgress.value = 0
  uploadRef.value?.clearFiles()
  clearError()
}

const handleAnalyze = async () => {
  if (uploadMode.value === 'single' && !selectedFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  if (uploadMode.value === 'batch' && selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择图片')
    return
  }

  // 重置状态
  analyzing.value = true
  uploadProgress.value = 0
  clearError()

  try {
    if (uploadMode.value === 'single' && selectedFile.value) {
      const result = await apiService.analyze(
        selectedFile.value,
        visualize.value,
        (progress: number) => {
          uploadProgress.value = progress
        }
      )

      ElMessage.success({
        message: '分析完成',
        duration: 2000
      })
      emit('result', result)
    } else {
      const result = await apiService.createBatchTask(
        selectedFiles.value,
        visualize.value,
        (progress: number) => {
          uploadProgress.value = progress
        }
      )

      ElMessage.success({
        message: `批量任务已创建，共 ${result.file_count} 张图片`,
        duration: 2000
      })
      emit('batchTask', result)
    }
  } catch (error: unknown) {
    console.error('Analysis failed:', error)

    if (error instanceof ApiError) {
      lastError.value = {
        message: error.message,
        detail: error.detail
      }
      // 使用 API 服务的错误显示（已有防抖）
      apiService.showError(error)
    } else if (error instanceof Error) {
      lastError.value = {
        message: error.message || '分析失败'
      }
      ElMessage.error(error.message || '分析失败，请重试')
    } else {
      lastError.value = {
        message: '分析失败，请重试'
      }
      ElMessage.error('分析失败，请重试')
    }
  } finally {
    analyzing.value = false
    uploadProgress.value = 0
  }
}
</script>

<style scoped>
.image-upload {
  width: 100%;
  padding: 20px;
  border-radius: 14px;
}

.upload-shell {
  margin-bottom: 18px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.upload-area {
  margin-bottom: 20px;
}

.upload-area:deep(.el-upload-dragger) {
  min-height: 238px;
  border-radius: 14px;
  border: 1px dashed rgba(15, 118, 110, 0.32);
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.08), rgba(245, 158, 11, 0.07)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(244, 246, 242, 0.86));
  transition:
    border-color 0.24s ease,
    transform 0.24s ease,
    box-shadow 0.24s ease;
}

.upload-area:deep(.el-upload-dragger:hover) {
  border-color: var(--brand);
  transform: translateY(-1px);
  box-shadow: 0 16px 32px rgba(15, 118, 110, 0.1);
}

.upload-area:deep(.el-upload-dragger.is-dragover) {
  border-color: var(--brand);
  background-color: rgba(15, 118, 110, 0.08);
}

.upload-visual {
  width: 92px;
  height: 92px;
  margin: 0 auto 16px;
  display: grid;
  place-items: center;
  border-radius: 22px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(245, 158, 11, 0.12)),
    rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.upload-icon {
  font-size: 58px;
  color: var(--brand);
  transition: color 0.3s ease;
}

.upload-area:deep(.el-upload-dragger:hover) .upload-icon {
  color: var(--accent);
}

.upload-text {
  color: var(--text-secondary);
}

.upload-text p {
  margin: 8px 0;
}

.upload-text em {
  color: var(--brand-strong);
  font-style: normal;
  font-weight: 800;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.preview-section {
  margin: 20px 0;
  text-align: center;
}

.preview-image {
  max-width: 100%;
  max-height: 400px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  margin-bottom: 10px;
}

.upload-options {
  margin: 20px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.batch-preview-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}

.batch-file-tag {
  max-width: 100%;
}

.progress-section {
  margin: 20px 0;
  padding: 16px;
  background-color: var(--surface-muted);
  border-radius: 12px;
}

.progress-text {
  margin-top: 12px;
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.progress-text .is-loading {
  animation: rotate 1s linear infinite;
}

.progress-icon,
.button-loading-icon {
  font-size: 18px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.analyze-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 700;
  border-radius: 12px;
}

.analyze-button .is-loading {
  margin-right: 8px;
}

.error-alert {
  margin-top: 20px;
}

/* 禁用状态样式 */
.upload-area:deep(.is-disabled .el-upload-dragger) {
  cursor: not-allowed;
  background-color: #f5f7f2;
}

.upload-area:deep(.is-disabled .el-upload-dragger:hover) {
  border-color: #dcdfe6;
}

@media (max-width: 768px) {
  .image-upload {
    padding: 18px;
  }

  .section-heading {
    flex-direction: column;
  }
}
</style>

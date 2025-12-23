<template>
  <div class="image-upload">
    <el-upload
      ref="uploadRef"
      class="upload-area"
      drag
      :auto-upload="false"
      :limit="1"
      :accept="acceptedFormats"
      :on-change="handleFileChange"
      :on-exceed="handleExceed"
      :file-list="fileList"
      :disabled="analyzing"
    >
      <el-icon class="upload-icon">
        <UploadFilled />
      </el-icon>
      <div class="upload-text">
        <p>拖拽图片到此处或<em>点击上传</em></p>
        <p class="upload-hint">支持 JPG/PNG/WEBP 格式，文件大小不超过 10MB</p>
      </div>
    </el-upload>

    <div v-if="previewUrl" class="preview-section">
      <el-image :src="previewUrl" fit="contain" class="preview-image" />
      <el-button type="danger" size="small" :disabled="analyzing" @click="clearFile">
        清除
      </el-button>
    </div>

    <div class="upload-options">
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
        <el-icon class="is-loading"><Loading /></el-icon>
        正在分析图片，请稍候...
      </p>
    </div>

    <el-button
      type="primary"
      :loading="analyzing"
      :disabled="!selectedFile || analyzing"
      class="analyze-button"
      @click="handleAnalyze"
    >
      <template #loading>
        <el-icon class="is-loading"><Loading /></el-icon>
      </template>
      {{ analyzeButtonText }}
    </el-button>

    <!-- 错误提示卡片 -->
    <el-alert
      v-if="lastError"
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
import { Loading, UploadFilled } from '@element-plus/icons-vue'
import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElIcon,
  ElImage,
  ElMessage,
  ElProgress,
  ElUpload
} from 'element-plus'
import { computed, ref } from 'vue'
import type { UploadFile, UploadFiles, UploadInstance } from 'element-plus'
import { apiService, ApiError } from '@/services/api'
import type { InferenceResponse } from '@/types/api'

const emit = defineEmits<{
  result: [data: InferenceResponse]
}>()

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const fileList = ref<UploadFiles>([])
const previewUrl = ref<string>('')
const visualize = ref(true)
const analyzing = ref(false)
const uploadProgress = ref(0)
const lastError = ref<{ message: string; detail?: string } | null>(null)

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

// 清除错误
const clearError = () => {
  lastError.value = null
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

  selectedFile.value = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
}

const handleExceed = () => {
  ElMessage.warning('一次只能上传一个文件，请先清除当前文件')
}

const clearFile = () => {
  selectedFile.value = null
  previewUrl.value = ''
  fileList.value = []
  uploadProgress.value = 0
  uploadRef.value?.clearFiles()
  clearError()
}

const handleAnalyze = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  // 重置状态
  analyzing.value = true
  uploadProgress.value = 0
  clearError()

  try {
    const result = await apiService.analyze(
      selectedFile.value,
      visualize.value,
      // 进度回调
      (progress: number) => {
        uploadProgress.value = progress
      }
    )

    ElMessage.success({
      message: '分析完成',
      duration: 2000
    })
    emit('result', result)
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
  max-width: 600px;
  margin: 0 auto;
}

.upload-area {
  margin-bottom: 20px;
}

.upload-area:deep(.el-upload-dragger) {
  transition: border-color 0.3s ease;
}

.upload-area:deep(.el-upload-dragger:hover) {
  border-color: #409eff;
}

.upload-area:deep(.el-upload-dragger.is-dragover) {
  border-color: #409eff;
  background-color: rgba(64, 158, 255, 0.06);
}

.upload-icon {
  font-size: 67px;
  color: #8c939d;
  margin-bottom: 16px;
  transition: color 0.3s ease;
}

.upload-area:deep(.el-upload-dragger:hover) .upload-icon {
  color: #409eff;
}

.upload-text {
  color: #606266;
}

.upload-text p {
  margin: 8px 0;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

.preview-section {
  margin: 20px 0;
  text-align: center;
}

.preview-image {
  max-width: 100%;
  max-height: 400px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin-bottom: 10px;
}

.upload-options {
  margin: 20px 0;
}

.progress-section {
  margin: 20px 0;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
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
  height: 44px;
  font-size: 16px;
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
  background-color: #f5f7fa;
}

.upload-area:deep(.is-disabled .el-upload-dragger:hover) {
  border-color: #dcdfe6;
}
</style>

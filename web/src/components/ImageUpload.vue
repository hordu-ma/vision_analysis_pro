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
      <el-button type="danger" size="small" @click="clearFile">清除</el-button>
    </div>

    <div class="upload-options">
      <el-checkbox v-model="visualize" label="生成可视化结果" />
    </div>

    <el-button
      type="primary"
      :loading="analyzing"
      :disabled="!selectedFile"
      class="analyze-button"
      @click="handleAnalyze"
    >
      {{ analyzing ? '分析中...' : '开始分析' }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'
import { ElButton, ElCheckbox, ElIcon, ElImage, ElMessage, ElUpload } from 'element-plus'
import { ref } from 'vue'
import type { UploadFile, UploadFiles, UploadInstance } from 'element-plus'
import { apiService } from '@/services/api'
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

const acceptedFormats = 'image/jpeg,image/png,image/jpg,image/webp'
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

const handleFileChange = (file: UploadFile) => {
  if (!file.raw) return

  // 验证文件大小
  if (file.raw.size > MAX_FILE_SIZE) {
    ElMessage.error('文件大小不能超过 10MB')
    fileList.value = []
    return
  }

  // 验证文件类型
  if (!acceptedFormats.includes(file.raw.type)) {
    ElMessage.error('仅支持 JPG/PNG/WEBP 格式')
    fileList.value = []
    return
  }

  selectedFile.value = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
}

const handleExceed = () => {
  ElMessage.warning('一次只能上传一个文件')
}

const clearFile = () => {
  selectedFile.value = null
  previewUrl.value = ''
  fileList.value = []
  uploadRef.value?.clearFiles()
}

const handleAnalyze = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  analyzing.value = true
  try {
    const result = await apiService.analyze(selectedFile.value, visualize.value)
    ElMessage.success('分析完成')
    emit('result', result)
  } catch (error: unknown) {
    console.error('Analysis failed:', error)
    const errorMessage =
      (error as { response?: { data?: { message?: string } } }).response?.data?.message ||
      '分析失败，请重试'
    ElMessage.error(errorMessage)
  } finally {
    analyzing.value = false
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

.upload-icon {
  font-size: 67px;
  color: #8c939d;
  margin-bottom: 16px;
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

.analyze-button {
  width: 100%;
}
</style>

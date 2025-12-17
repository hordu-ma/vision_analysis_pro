<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <h1>Vision Analysis Pro</h1>
        <HealthStatus />
      </el-header>
      <el-main>
        <ImageUpload @result="handleResult" />
        <DetectionResult :result="detectionResult" />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ElContainer, ElHeader, ElMain } from 'element-plus'
import { ref } from 'vue'
import DetectionResult from '@/components/DetectionResult.vue'
import HealthStatus from '@/components/HealthStatus.vue'
import ImageUpload from '@/components/ImageUpload.vue'
import type { InferenceResponse } from '@/types/api'

const detectionResult = ref<InferenceResponse | null>(null)

const handleResult = (data: InferenceResponse) => {
  detectionResult.value = data
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.el-main {
  padding: 40px 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>

# Vision Analysis Pro - 前端项目

基于 Vue 3 + TypeScript + Vite + Element Plus 构建的视觉分析系统前端应用。

## 技术栈

- **框架**: Vue 3.5+ (Composition API)
- **语言**: TypeScript 5.9+
- **构建工具**: Vite 7.2+
- **UI 组件库**: Element Plus 2.12+
- **状态管理**: Pinia 3.0+
- **HTTP 客户端**: Axios 1.13+
- **测试框架**: Vitest 4.0+
- **代码规范**: ESLint + Prettier

## 项目结构

```
web/
├── public/                 # 静态资源
├── src/
│   ├── components/         # Vue 组件
│   │   ├── DetectionResult.vue      # 检测结果展示
│   │   ├── HealthStatus.vue         # 健康状态检查
│   │   └── ImageUpload.vue          # 图片上传
│   ├── services/           # 服务层
│   │   └── api.ts          # API 接口封装
│   ├── types/              # TypeScript 类型定义
│   │   └── api.ts          # API 相关类型
│   ├── App.vue             # 根组件
│   ├── main.ts             # 应用入口
│   ├── env.d.ts            # 环境类型声明
│   └── style.css           # 全局样式
├── *.spec.ts               # 测试文件
├── index.html              # HTML 模板
├── vite.config.ts          # Vite 配置
├── vitest.config.ts        # Vitest 配置
├── tsconfig.json           # TypeScript 配置
└── package.json            # 项目依赖
```

## 快速开始

### 环境要求

- Node.js >= 20.0.0
- npm >= 9.0.0

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建产物位于 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

### 运行测试

```bash
# 一次性运行
npm test -- --run

# 监听模式
npm test
```

### 代码检查

```bash
# ESLint 检查
npm run lint

# 代码格式化
npm run format
```

## 核心功能

### 1. 图片上传 (ImageUpload)

**功能**:

- 支持拖拽上传
- 文件类型验证 (.jpg, .png, .webp)
- 文件大小限制 (10MB)
- 本地图片预览
- 上传前验证

**使用示例**:

```vue
<ImageUpload @result="handleResult" />
```

### 2. 检测结果展示 (DetectionResult)

**功能**:

- 检测统计信息（数量、平均置信度、推理时间）
- 可视化图片展示
- 检测详情表格
- 边界框坐标显示

**使用示例**:

```vue
<DetectionResult :result="detectionResult" />
```

### 3. 健康状态检查 (HealthStatus)

**功能**:

- 自动检查服务状态
- 显示服务健康信息
- Popover 显示详细信息（引擎、模型状态、版本）

**使用示例**:

```vue
<HealthStatus />
```

## API 接口

### 基础配置

```typescript
// src/services/api.ts
baseURL: '/api/v1'
timeout: 30000 // 30秒
```

### 接口列表

#### 1. 健康检查

```typescript
apiService.health(): Promise<HealthResponse>
```

**响应**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "model_loaded": true,
  "engine": "YOLOInferenceEngine"
}
```

#### 2. 图片推理

```typescript
apiService.analyze(file: File, visualize?: boolean): Promise<InferenceResponse>
```

**参数**:

- `file`: 图片文件
- `visualize`: 是否返回可视化图片（后端默认 false；前端调用默认 true）

**响应**:

```json
{
  "filename": "test.jpg",
  "detections": [
    {
      "label": "crack",
      "confidence": 0.95,
      "bbox": [100, 150, 300, 400]
    }
  ],
  "metadata": {
    "engine": "YOLOInferenceEngine",
    "inference_time_ms": 123.45
  },
  "visualization": "data:image/jpeg;base64,..."
}
```

## 开发指南

### 代理配置

开发环境下，前端请求会自动代理到后端 API：

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

### 类型安全

项目使用 TypeScript 严格模式，所有 API 接口都有完整的类型定义：

```typescript
// src/types/api.ts
export interface DetectionBox {
  label: string
  confidence: number
  bbox: [number, number, number, number]
}

export interface InferenceResponse {
  filename: string
  detections: DetectionBox[]
  metadata: {
    inference_time_ms?: number
    model_version?: string
    engine?: string
  }
  visualization?: string
}
```

### 错误处理

当前错误处理在组件层实现，使用 `try-catch` 捕获异常：

```typescript
try {
  const result = await apiService.analyze(file)
  ElMessage.success('分析完成')
} catch (error: unknown) {
  const errorMessage =
    (error as { response?: { data?: { message?: string } } }).response?.data?.message ||
    '分析失败，请重试'
  ElMessage.error(errorMessage)
}
```

后续计划（与总体进度对齐）：

- 补充全局错误拦截器（axios 拦截器 + 统一提示）与错误边界
- 体验优化：加载/骨架、上传进度、缩放与快捷键
- 评估 Pinia：保留或移除，或用于历史记录/设置
- 构建与性能：Element Plus 按需、代码分割、生产构建与预览

## 测试

### 测试覆盖

- **DetectionResult**: 6 个测试用例
- **HealthStatus**: 7 个测试用例
- **API Service**: 6 个测试用例
- **总计**: 19 个测试用例 ✅

### 测试命令

```bash
# 运行所有测试
npm test -- --run

# 运行特定测试文件
npm test -- --run src/components/DetectionResult.spec.ts

# 查看测试覆盖率（需要安装 @vitest/coverage-v8）
npm test -- --run --coverage
```

## 部署

### 生产构建

```bash
# 构建
npm run build

# 构建产物
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── ...
```

### 环境变量

创建 `.env.production` 配置生产环境变量：

```bash
# API 基础路径（如果需要）
VITE_API_BASE_URL=https://api.example.com
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 常见问题

### 1. 端口被占用

修改 `vite.config.ts` 中的端口配置：

```typescript
server: {
  port: 5173 // 修改为其他端口
}
```

### 2. API 请求失败

检查后端服务是否启动：

```bash
curl http://localhost:8000/api/v1/health
```

### 3. 类型错误

确保已安装类型声明文件，并检查 `tsconfig.json` 配置。

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## 许可证

MIT

## 相关链接

- [Vue 3 文档](https://vuejs.org/)
- [Vite 文档](https://vitejs.dev/)
- [Element Plus 文档](https://element-plus.org/)
- [Vitest 文档](https://vitest.dev/)

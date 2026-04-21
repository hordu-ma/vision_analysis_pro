import { expect, test } from '@playwright/test'

const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAWUlEQVRIDbXBAQEAAAABIP7faaAVqshTkaciT0WeijwVeSryVOSpyFORpyJPRZ6KPBV5KvJU5KnIU5GnIk9Fnoo8FXkq8lTkqchTkaciT0WeijwVeSryVORpZ6pDof93QNwAAAAASUVORK5CYII='

test('上传图片后展示检测结果', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByTestId('health-status-text')).toContainText(/模型未加载|服务正常/)

  await page.locator('input[type="file"]').setInputFiles({
    name: 'tower.png',
    mimeType: 'image/png',
    buffer: Buffer.from(PNG_BASE64, 'base64')
  })

  await expect(page.getByTestId('image-preview')).toBeVisible()

  await page.getByTestId('analyze-button').click()

  await expect(page.getByTestId('detection-result')).toBeVisible()
  await expect(page.getByTestId('detection-count')).toContainText('3')
  await expect(page.getByText('首要缺陷')).toBeVisible()
  await expect(page.getByRole('heading', { name: '裂缝' })).toBeVisible()
})

test('批量任务完成后展示任务结果', async ({ page }) => {
  const createTaskResponse = await page.request.post(
    '/api/v1/inference/images/tasks?visualize=false',
    {
      multipart: {
        files: {
          name: 'tower-a.png',
          mimeType: 'image/png',
          buffer: Buffer.from(PNG_BASE64, 'base64')
        }
      }
    }
  )
  expect(createTaskResponse.status()).toBe(202)
  const task = await createTaskResponse.json()
  const taskId = String(task.task_id)
  let taskCompleted = false

  for (let index = 0; index < 20; index += 1) {
    const taskResponse = await page.request.get(`/api/v1/inference/images/tasks/${taskId}`)
    const taskDetail = await taskResponse.json()
    if (taskDetail.status === 'completed') {
      taskCompleted = true
      break
    }
    await page.waitForTimeout(100)
  }
  expect(taskCompleted).toBe(true)

  await page.goto('/')
  await expect(page.getByText(taskId)).toBeVisible()
  await page.getByText(taskId).click()

  await expect(page.getByTestId('batch-task-status')).toBeVisible()
  await expect(page.getByText('已完成').first()).toBeVisible()
  await expect(page.getByText('批量分析结果')).toBeVisible()
})

test('上报批次可在工作台打开并保存复核', async ({ page }) => {
  const batchId = `edge-e2e-${Date.now()}`
  const deviceId = `edge-device-e2e-${Date.now()}`

  const reportResponse = await page.request.post('/api/v1/report', {
    data: {
      device_id: deviceId,
      batch_id: batchId,
      report_time: 1700000000.0,
      results: [
        {
          frame_id: 1,
          timestamp: 1700000000.0,
          source_id: deviceId,
          detections: [
            {
              label: 'crack',
              confidence: 0.95,
              bbox: [100.0, 150.0, 300.0, 400.0]
            }
          ],
          inference_time_ms: 12.4,
          metadata: { image_name: 'tower-e2e.jpg' }
        }
      ]
    }
  })
  expect(reportResponse.status()).toBe(202)

  await page.goto('/')
  const batchItem = page.locator('article.record-item').filter({ hasText: deviceId }).first()
  await expect(batchItem).toBeVisible()
  await batchItem.click()

  const drawer = page.locator('.el-drawer')
  await expect(drawer.getByRole('heading', { name: batchId })).toBeVisible()
  await drawer.getByText('帧 1 · 待处理').click()
  await drawer.getByRole('textbox', { name: '复核人' }).fill('e2e-reviewer')
  await drawer.getByRole('textbox', { name: '备注' }).fill('浏览器复核 smoke')
  await drawer.getByRole('button', { name: '保存复核' }).click()

  await expect(drawer.getByText('e2e-reviewer')).toBeVisible()
})

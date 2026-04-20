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

"""演示如何调用推理 API 并保存可视化结果

运行前请确保 API 服务已启动：
    uv run uvicorn vision_analysis_pro.web.api.main:app --reload

使用方法：
    python examples/demo_request.py <image_path>

示例：
    python examples/demo_request.py test_image.jpg
"""

import base64
import sys
from pathlib import Path

import cv2
import httpx
import numpy as np


def create_test_image(output_path: str = "test_image.jpg") -> None:
    """创建一个简单的测试图片"""
    # 创建 640x480 的灰色图像
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)  # 浅灰色背景

    # 添加一些形状以便可视化检测框
    # 绘制一个矩形（模拟裂缝区域）
    cv2.rectangle(img, (100, 150), (300, 400), (150, 150, 150), -1)

    # 绘制一个圆形（模拟锈蚀区域）
    cv2.circle(img, (500, 275), 50, (100, 100, 100), -1)

    # 保存图像
    cv2.imwrite(output_path, img)
    print(f"✅ 测试图像已创建: {output_path}")


def send_inference_request(
    image_path: str,
    api_url: str = "http://127.0.0.1:8000/api/v1/inference/image",
    visualize: bool = True,
) -> dict:
    """发送推理请求到 API

    Args:
        image_path: 图像文件路径
        api_url: API 端点 URL
        visualize: 是否返回可视化结果

    Returns:
        API 响应的 JSON 数据
    """
    print(f"\n📤 发送推理请求: {image_path}")

    with open(image_path, "rb") as f:
        files = {"file": (Path(image_path).name, f, "image/jpeg")}
        url = f"{api_url}?visualize={str(visualize).lower()}"

        try:
            response = httpx.post(url, files=files, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP 错误: {e.response.status_code}")
            print(f"   详情: {e.response.text}")
            sys.exit(1)
        except httpx.RequestError as e:
            print(f"❌ 请求错误: {e}")
            print("   提示: 请确保 API 服务已启动")
            sys.exit(1)


def save_visualization(
    base64_data_uri: str, output_path: str = "output_visualization.jpg"
) -> None:
    """从 base64 Data URI 保存可视化图像

    Args:
        base64_data_uri: base64 编码的 Data URI（如 "data:image/jpeg;base64,..."）
        output_path: 输出文件路径
    """
    # 提取 base64 数据部分
    if "base64," in base64_data_uri:
        base64_data = base64_data_uri.split("base64,")[1]
    else:
        base64_data = base64_data_uri

    # 解码并保存
    img_bytes = base64.b64decode(base64_data)
    Path(output_path).write_bytes(img_bytes)
    print(f"✅ 可视化图像已保存: {output_path}")


def print_detection_results(data: dict) -> None:
    """打印检测结果"""
    print("\n📊 推理结果:")
    print(f"   文件名: {data['filename']}")
    print(f"   引擎: {data['metadata'].get('engine', 'N/A')}")
    print(f"   检测到 {len(data['detections'])} 个目标:\n")

    for i, det in enumerate(data["detections"], 1):
        bbox = det["bbox"]
        print(f"   {i}. {det['label']} (置信度: {det['confidence']:.2f})")
        print(
            f"      位置: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]"
        )


def main() -> None:
    """主函数"""
    print("=" * 60)
    print("  Vision Analysis Pro - Demo 演示脚本")
    print("=" * 60)

    # 获取图像路径
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 如果没有提供路径，创建测试图像
        image_path = "test_image.jpg"
        if not Path(image_path).exists():
            create_test_image(image_path)

    # 验证文件存在
    if not Path(image_path).exists():
        print(f"❌ 错误: 文件不存在: {image_path}")
        print("\n使用方法: python examples/demo_request.py <image_path>")
        sys.exit(1)

    # 发送推理请求（带可视化）
    data = send_inference_request(image_path, visualize=True)

    # 打印检测结果
    print_detection_results(data)

    # 保存可视化图像
    if data.get("visualization"):
        save_visualization(data["visualization"], "output_visualization.jpg")
    else:
        print("\n⚠️  未返回可视化数据（可能检测结果为空）")

    print("\n" + "=" * 60)
    print("✨ Demo 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

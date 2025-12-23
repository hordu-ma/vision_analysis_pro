"""边缘 Agent 核心模块单元测试"""

import time
from pathlib import Path

import numpy as np
import pytest

from vision_analysis_pro.edge_agent import (
    CacheConfig,
    Detection,
    EdgeAgentConfig,
    FrameData,
    InferenceConfig,
    InferenceResult,
    ReporterConfig,
    ReportPayload,
    SourceConfig,
    SourceType,
)
from vision_analysis_pro.edge_agent.reporters.cache import CacheManager
from vision_analysis_pro.edge_agent.sources import create_source
from vision_analysis_pro.edge_agent.sources.folder import FolderSource
from vision_analysis_pro.edge_agent.sources.video import VideoSource

# ============================================================================
# 数据模型测试
# ============================================================================


class TestFrameData:
    """FrameData 数据模型测试"""

    def test_create_frame_data(self) -> None:
        """测试创建 FrameData"""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = time.time()

        frame = FrameData(
            image=image,
            timestamp=timestamp,
            source_id="test-source",
            frame_id=1,
            metadata={"key": "value"},
        )

        assert frame.source_id == "test-source"
        assert frame.frame_id == 1
        assert frame.timestamp == timestamp
        assert frame.shape == (480, 640, 3)
        assert frame.metadata == {"key": "value"}

    def test_frame_data_datetime(self) -> None:
        """测试 datetime 属性"""
        timestamp = 1700000000.0
        frame = FrameData(
            image=np.zeros((100, 100, 3), dtype=np.uint8),
            timestamp=timestamp,
            source_id="test",
        )

        dt = frame.datetime
        assert dt.timestamp() == timestamp


class TestDetection:
    """Detection 数据模型测试"""

    def test_create_detection(self) -> None:
        """测试创建 Detection"""
        detection = Detection(
            label="crack",
            confidence=0.95,
            bbox=[100.0, 200.0, 300.0, 400.0],
        )

        assert detection.label == "crack"
        assert detection.confidence == 0.95
        assert detection.bbox == [100.0, 200.0, 300.0, 400.0]

    def test_detection_to_dict(self) -> None:
        """测试转换为字典"""
        detection = Detection(
            label="rust",
            confidence=0.85,
            bbox=[10.0, 20.0, 30.0, 40.0],
        )

        d = detection.to_dict()
        assert d["label"] == "rust"
        assert d["confidence"] == 0.85
        assert d["bbox"] == [10.0, 20.0, 30.0, 40.0]

    def test_detection_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "label": "corrosion",
            "confidence": 0.75,
            "bbox": [50.0, 60.0, 70.0, 80.0],
        }

        detection = Detection.from_dict(data)
        assert detection.label == "corrosion"
        assert detection.confidence == 0.75
        assert detection.bbox == [50.0, 60.0, 70.0, 80.0]


class TestInferenceResult:
    """InferenceResult 数据模型测试"""

    def test_create_inference_result(self) -> None:
        """测试创建 InferenceResult"""
        detections = [
            Detection(label="crack", confidence=0.9, bbox=[0, 0, 100, 100]),
            Detection(label="rust", confidence=0.8, bbox=[100, 100, 200, 200]),
        ]

        result = InferenceResult(
            frame_id=1,
            timestamp=time.time(),
            source_id="test",
            detections=detections,
            inference_time_ms=15.5,
        )

        assert result.has_detections is True
        assert result.detection_count == 2
        assert result.inference_time_ms == 15.5

    def test_inference_result_no_detections(self) -> None:
        """测试无检测结果"""
        result = InferenceResult(
            frame_id=1,
            timestamp=time.time(),
            source_id="test",
            detections=[],
        )

        assert result.has_detections is False
        assert result.detection_count == 0

    def test_inference_result_serialization(self) -> None:
        """测试序列化"""
        detections = [Detection(label="crack", confidence=0.9, bbox=[0, 0, 100, 100])]
        result = InferenceResult(
            frame_id=1,
            timestamp=1700000000.0,
            source_id="test",
            detections=detections,
            inference_time_ms=10.0,
            metadata={"key": "value"},
        )

        d = result.to_dict()
        assert d["frame_id"] == 1
        assert d["timestamp"] == 1700000000.0
        assert len(d["detections"]) == 1
        assert d["detections"][0]["label"] == "crack"

        # 反序列化
        restored = InferenceResult.from_dict(d)
        assert restored.frame_id == 1
        assert restored.detection_count == 1
        assert restored.detections[0].label == "crack"


class TestReportPayload:
    """ReportPayload 数据模型测试"""

    def test_create_report_payload(self) -> None:
        """测试创建 ReportPayload"""
        results = [
            InferenceResult(
                frame_id=1,
                timestamp=time.time(),
                source_id="test",
                detections=[
                    Detection(label="crack", confidence=0.9, bbox=[0, 0, 100, 100])
                ],
            )
        ]

        payload = ReportPayload(device_id="edge-001", results=results)

        assert payload.device_id == "edge-001"
        assert payload.result_count == 1
        assert payload.total_detections == 1
        assert payload.batch_id.startswith("edge-001-")

    def test_report_payload_to_dict(self) -> None:
        """测试转换为字典"""
        results = [
            InferenceResult(
                frame_id=1,
                timestamp=1700000000.0,
                source_id="test",
                detections=[],
            )
        ]

        payload = ReportPayload(
            device_id="edge-001",
            results=results,
            report_time=1700000000.0,
            batch_id="test-batch",
        )

        d = payload.to_dict()
        assert d["device_id"] == "edge-001"
        assert d["batch_id"] == "test-batch"
        assert len(d["results"]) == 1


# ============================================================================
# 配置测试
# ============================================================================


class TestSourceConfig:
    """SourceConfig 配置测试"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = SourceConfig()

        assert config.type == SourceType.VIDEO
        assert config.path == "0"
        assert config.fps_limit == 0.0
        assert config.loop is False

    def test_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "type": "folder",
            "path": "/path/to/images",
            "fps_limit": 10.0,
            "loop": True,
        }

        config = SourceConfig.from_dict(data)
        assert config.type == SourceType.FOLDER
        assert config.path == "/path/to/images"
        assert config.fps_limit == 10.0
        assert config.loop is True


class TestInferenceConfig:
    """InferenceConfig 配置测试"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = InferenceConfig()

        assert config.engine == "onnx"
        assert config.model_path == "models/best.onnx"
        assert config.confidence == 0.5
        assert config.iou == 0.5

    def test_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "engine": "yolo",
            "model_path": "models/custom.pt",
            "confidence": 0.7,
        }

        config = InferenceConfig.from_dict(data)
        assert config.engine == "yolo"
        assert config.model_path == "models/custom.pt"
        assert config.confidence == 0.7


class TestEdgeAgentConfig:
    """EdgeAgentConfig 配置测试"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = EdgeAgentConfig()

        assert config.device_id == "edge-agent-001"
        assert config.log_level == "INFO"
        assert isinstance(config.source, SourceConfig)
        assert isinstance(config.inference, InferenceConfig)

    def test_from_dict(self) -> None:
        """测试从字典创建"""
        data = {
            "device_id": "custom-device",
            "log_level": "DEBUG",
            "source": {"type": "folder", "path": "/images"},
            "inference": {"engine": "yolo"},
        }

        config = EdgeAgentConfig.from_dict(data)
        assert config.device_id == "custom-device"
        assert config.log_level == "DEBUG"
        assert config.source.type == SourceType.FOLDER
        assert config.inference.engine == "yolo"

    def test_from_yaml(self, tmp_path: Path) -> None:
        """测试从 YAML 文件加载"""
        yaml_content = """
device_id: "yaml-device"
log_level: "WARNING"
source:
  type: video
  path: "/path/to/video.mp4"
inference:
  engine: onnx
  confidence: 0.6
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        config = EdgeAgentConfig.from_yaml(config_file)
        assert config.device_id == "yaml-device"
        assert config.log_level == "WARNING"
        assert config.source.type == SourceType.VIDEO
        assert config.inference.confidence == 0.6

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """测试从环境变量加载"""
        monkeypatch.setenv("EDGE_AGENT_DEVICE_ID", "env-device")
        monkeypatch.setenv("EDGE_AGENT_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("EDGE_AGENT_SOURCE_TYPE", "rtsp")
        monkeypatch.setenv("EDGE_AGENT_SOURCE_PATH", "rtsp://example.com/stream")

        config = EdgeAgentConfig.from_env()
        assert config.device_id == "env-device"
        assert config.log_level == "ERROR"
        assert config.source.type == SourceType.RTSP
        assert config.source.path == "rtsp://example.com/stream"

    def test_validate_valid_config(self, tmp_path: Path) -> None:
        """测试验证有效配置"""
        # 创建模型文件
        model_file = tmp_path / "model.onnx"
        model_file.touch()

        # 创建数据源
        source_dir = tmp_path / "images"
        source_dir.mkdir()

        config = EdgeAgentConfig(
            inference=InferenceConfig(model_path=str(model_file)),
            source=SourceConfig(type=SourceType.FOLDER, path=str(source_dir)),
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_config(self) -> None:
        """测试验证无效配置"""
        config = EdgeAgentConfig(
            inference=InferenceConfig(
                model_path="/nonexistent/model.onnx",
                confidence=1.5,  # 无效
            ),
            source=SourceConfig(type=SourceType.VIDEO, path="/nonexistent/video.mp4"),
        )

        errors = config.validate()
        assert len(errors) > 0
        assert any("置信度" in e for e in errors)
        assert any("模型文件" in e for e in errors)


# ============================================================================
# 缓存管理器测试
# ============================================================================


class TestCacheManager:
    """CacheManager 缓存管理器测试"""

    @pytest.fixture
    def cache_config(self, tmp_path: Path) -> CacheConfig:
        """创建测试用缓存配置"""
        return CacheConfig(
            enabled=True,
            db_path=str(tmp_path / "test_cache.db"),
            max_entries=100,
            max_age_hours=1.0,
        )

    @pytest.fixture
    def cache_manager(self, cache_config: CacheConfig) -> CacheManager:
        """创建测试用缓存管理器"""
        manager = CacheManager(cache_config)
        manager.open()
        yield manager
        manager.close()

    def test_open_close(self, cache_config: CacheConfig) -> None:
        """测试打开和关闭"""
        manager = CacheManager(cache_config)

        assert manager.is_open is False
        manager.open()
        assert manager.is_open is True
        manager.close()
        assert manager.is_open is False

    def test_add_and_get(self, cache_manager: CacheManager) -> None:
        """测试添加和获取"""
        payload = ReportPayload(
            device_id="test-device",
            results=[
                InferenceResult(
                    frame_id=1,
                    timestamp=time.time(),
                    source_id="test",
                    detections=[],
                )
            ],
        )

        entry_id = cache_manager.add(payload)
        assert entry_id > 0

        entry = cache_manager.get(entry_id)
        assert entry is not None
        assert entry.payload.device_id == "test-device"

    def test_get_pending(self, cache_manager: CacheManager) -> None:
        """测试获取待处理条目"""
        # 添加多个条目
        for i in range(5):
            payload = ReportPayload(
                device_id=f"device-{i}",
                results=[],
            )
            cache_manager.add(payload)

        entries = cache_manager.get_pending(limit=3)
        assert len(entries) == 3

    def test_remove(self, cache_manager: CacheManager) -> None:
        """测试移除"""
        payload = ReportPayload(device_id="test", results=[])
        entry_id = cache_manager.add(payload)

        assert cache_manager.count() == 1
        assert cache_manager.remove(entry_id) is True
        assert cache_manager.count() == 0

    def test_update_retry(self, cache_manager: CacheManager) -> None:
        """测试更新重试计数"""
        payload = ReportPayload(device_id="test", results=[])
        entry_id = cache_manager.add(payload)

        cache_manager.update_retry(entry_id, "Connection refused")

        entry = cache_manager.get(entry_id)
        assert entry is not None
        assert entry.retry_count == 1
        assert "Connection refused" in entry.last_error

    def test_clear(self, cache_manager: CacheManager) -> None:
        """测试清空"""
        for i in range(5):
            cache_manager.add(ReportPayload(device_id=f"device-{i}", results=[]))

        assert cache_manager.count() == 5
        cleared = cache_manager.clear()
        assert cleared == 5
        assert cache_manager.count() == 0

    def test_cleanup_overflow(self, cache_config: CacheConfig) -> None:
        """测试溢出清理"""
        cache_config.max_entries = 5
        manager = CacheManager(cache_config)
        manager.open()

        try:
            # 添加超过最大数量的条目
            for i in range(10):
                manager.add(ReportPayload(device_id=f"device-{i}", results=[]))

            # 清理溢出
            removed = manager.cleanup_overflow()
            assert removed == 5
            assert manager.count() == 5
        finally:
            manager.close()

    def test_get_stats(self, cache_manager: CacheManager) -> None:
        """测试获取统计信息"""
        cache_manager.add(ReportPayload(device_id="test", results=[]))

        stats = cache_manager.get_stats()
        assert stats["is_open"] is True
        assert stats["count"] == 1
        assert "db_path" in stats

    def test_context_manager(self, cache_config: CacheConfig) -> None:
        """测试上下文管理器"""
        with CacheManager(cache_config) as manager:
            assert manager.is_open is True
            manager.add(ReportPayload(device_id="test", results=[]))

        # 退出后应该关闭
        assert manager.is_open is False


# ============================================================================
# 数据源测试
# ============================================================================


class TestFolderSource:
    """FolderSource 数据源测试"""

    @pytest.fixture
    def image_folder(self, tmp_path: Path) -> Path:
        """创建测试用图像文件夹"""
        folder = tmp_path / "images"
        folder.mkdir()

        # 创建测试图像
        import cv2

        for i in range(3):
            img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(folder / f"image_{i:03d}.jpg"), img)

        return folder

    def test_open_close(self, image_folder: Path) -> None:
        """测试打开和关闭"""
        config = SourceConfig(type=SourceType.FOLDER, path=str(image_folder))
        source = FolderSource(config, "test-folder")

        assert source.is_open is False
        source.open()
        assert source.is_open is True
        assert source.total_images == 3
        source.close()
        assert source.is_open is False

    def test_read_frames(self, image_folder: Path) -> None:
        """测试读取帧"""
        config = SourceConfig(type=SourceType.FOLDER, path=str(image_folder))
        source = FolderSource(config, "test-folder")

        with source:
            frames = list(source)

        assert len(frames) == 3
        for i, frame in enumerate(frames):
            assert isinstance(frame, FrameData)
            assert frame.source_id == "test-folder"
            assert frame.image.shape == (100, 100, 3)

    def test_folder_not_exists(self) -> None:
        """测试文件夹不存在"""
        config = SourceConfig(type=SourceType.FOLDER, path="/nonexistent/folder")
        source = FolderSource(config)

        with pytest.raises(FileNotFoundError):
            source.open()

    def test_empty_folder(self, tmp_path: Path) -> None:
        """测试空文件夹"""
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()

        config = SourceConfig(type=SourceType.FOLDER, path=str(empty_folder))
        source = FolderSource(config)

        with pytest.raises(ValueError, match="没有支持的图像文件"):
            source.open()

    def test_progress(self, image_folder: Path) -> None:
        """测试进度属性"""
        config = SourceConfig(type=SourceType.FOLDER, path=str(image_folder))
        source = FolderSource(config)

        with source:
            assert source.progress == 0.0
            source.read_frame()
            assert 0 < source.progress < 1
            source.read_frame()
            source.read_frame()
            assert source.progress == 1.0


class TestCreateSource:
    """create_source 工厂函数测试"""

    def test_create_folder_source(self, tmp_path: Path) -> None:
        """测试创建文件夹数据源"""
        folder = tmp_path / "images"
        folder.mkdir()

        config = SourceConfig(type=SourceType.FOLDER, path=str(folder))
        source = create_source(config, "test")

        assert isinstance(source, FolderSource)

    def test_create_video_source(self) -> None:
        """测试创建视频数据源"""
        config = SourceConfig(type=SourceType.VIDEO, path="video.mp4")
        source = create_source(config, "test")

        assert isinstance(source, VideoSource)

    def test_invalid_source_type(self) -> None:
        """测试无效的数据源类型"""
        config = SourceConfig()
        config.type = "invalid"  # type: ignore

        with pytest.raises(ValueError, match="不支持的数据源类型"):
            create_source(config)


# ============================================================================
# 集成测试
# ============================================================================


class TestEdgeAgentIntegration:
    """EdgeAgent 集成测试"""

    @pytest.fixture
    def test_setup(self, tmp_path: Path):
        """创建测试环境"""
        # 创建图像文件夹
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        import cv2

        for i in range(3):
            img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(images_dir / f"img_{i}.jpg"), img)

        # 创建配置
        config = EdgeAgentConfig(
            device_id="test-agent",
            log_level="DEBUG",
            source=SourceConfig(type=SourceType.FOLDER, path=str(images_dir)),
            inference=InferenceConfig(
                engine="onnx",
                model_path="models/best.onnx",  # 会在测试中 mock
            ),
            reporter=ReporterConfig(
                url="http://localhost:8000/api/v1/report",
                batch_size=10,
            ),
            cache=CacheConfig(
                enabled=True,
                db_path=str(tmp_path / "cache.db"),
            ),
            report_only_detections=False,
        )

        return {
            "images_dir": images_dir,
            "config": config,
            "tmp_path": tmp_path,
        }

    def test_config_yaml_round_trip(self, tmp_path: Path) -> None:
        """测试配置文件往返"""
        import yaml

        config_data = {
            "device_id": "test-device",
            "source": {
                "type": "folder",
                "path": "/test/path",
            },
            "inference": {
                "engine": "onnx",
                "confidence": 0.7,
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = EdgeAgentConfig.from_yaml(config_file)
        assert config.device_id == "test-device"
        assert config.source.path == "/test/path"
        assert config.inference.confidence == 0.7

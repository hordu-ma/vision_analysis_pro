"""训练相关测试"""

from pathlib import Path

import pytest


class TestTrainingScripts:
    """测试训练脚本功能"""

    def test_train_script_exists(self) -> None:
        """测试训练脚本文件存在"""
        script_path = Path("scripts/train.py")
        assert script_path.exists(), "训练脚本不存在"
        assert script_path.is_file(), "训练脚本不是文件"

    def test_evaluate_script_exists(self) -> None:
        """测试评估脚本文件存在"""
        script_path = Path("scripts/evaluate.py")
        assert script_path.exists(), "评估脚本不存在"
        assert script_path.is_file(), "评估脚本不是文件"

    def test_data_yaml_exists(self) -> None:
        """测试数据配置文件存在"""
        data_yaml = Path("data/data.yaml")
        assert data_yaml.exists(), "data.yaml 不存在"

        # 读取并验证配置
        import yaml

        with data_yaml.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "path" in config, "缺少 path 配置"
        assert "train" in config, "缺少 train 配置"
        assert "val" in config, "缺少 val 配置"
        assert "nc" in config, "缺少 nc 配置"
        assert "names" in config, "缺少 names 配置"
        assert config["nc"] == 5, "类别数应为 5"
        assert len(config["names"]) == 5, "类别名称列表长度应为 5"

    def test_training_output_structure(self) -> None:
        """测试训练输出目录结构"""
        # 检查训练输出目录是否存在（如果已运行过训练）
        exp_dir = Path("runs/train/exp")
        if not exp_dir.exists():
            pytest.skip("训练尚未运行，跳过输出结构测试")

        # 验证必要文件
        weights_dir = exp_dir / "weights"
        assert weights_dir.exists(), "weights 目录不存在"

        best_pt = weights_dir / "best.pt"
        last_pt = weights_dir / "last.pt"
        assert best_pt.exists(), "best.pt 不存在"
        assert last_pt.exists(), "last.pt 不存在"

        # 验证训练日志
        results_csv = exp_dir / "results.csv"
        assert results_csv.exists(), "results.csv 不存在"

        args_yaml = exp_dir / "args.yaml"
        assert args_yaml.exists(), "args.yaml 不存在"

    def test_model_weights_reproducibility(self) -> None:
        """测试模型权重可复现性（通过配置文件）"""
        exp_dir = Path("runs/train/exp")
        if not exp_dir.exists():
            pytest.skip("训练尚未运行，跳过可复现性测试")

        args_yaml = exp_dir / "args.yaml"
        if not args_yaml.exists():
            pytest.skip("args.yaml 不存在，跳过测试")

        import yaml

        with args_yaml.open("r", encoding="utf-8") as f:
            args = yaml.safe_load(f)

        # 验证固定参数
        assert "seed" in args, "缺少 seed 参数"
        assert args["seed"] == 42, "随机种子应为 42"
        assert "deterministic" in args, "缺少 deterministic 参数"
        assert args["deterministic"] is True, "deterministic 应为 True"


class TestTrainingData:
    """测试训练数据"""

    def test_train_images_exist(self) -> None:
        """测试训练图像存在"""
        train_img_dir = Path("data/images/train")
        assert train_img_dir.exists(), "训练图像目录不存在"

        # 检查是否有图像
        images = list(train_img_dir.glob("*.jpg")) + list(train_img_dir.glob("*.png"))
        assert len(images) > 0, "训练集无图像"

    def test_val_images_exist(self) -> None:
        """测试验证图像存在"""
        val_img_dir = Path("data/images/val")
        assert val_img_dir.exists(), "验证图像目录不存在"

        # 检查是否有图像
        images = list(val_img_dir.glob("*.jpg")) + list(val_img_dir.glob("*.png"))
        assert len(images) > 0, "验证集无图像"

    def test_train_labels_match_images(self) -> None:
        """测试训练标签与图像匹配"""
        train_img_dir = Path("data/images/train")
        train_label_dir = Path("data/labels/train")

        if not train_img_dir.exists():
            pytest.skip("训练图像目录不存在")

        images = list(train_img_dir.glob("*.jpg")) + list(train_img_dir.glob("*.png"))
        for img_path in images:
            label_path = train_label_dir / f"{img_path.stem}.txt"
            # 标签文件可以不存在（无目标的图像）
            if label_path.exists():
                # 验证标签格式
                with label_path.open("r") as f:
                    lines = f.readlines()
                    for line in lines:
                        parts = line.strip().split()
                        assert len(parts) == 5, f"标签格式错误: {line}"
                        class_id = int(parts[0])
                        assert 0 <= class_id < 5, f"类别 ID 超出范围: {class_id}"

    def test_val_labels_match_images(self) -> None:
        """测试验证标签与图像匹配"""
        val_img_dir = Path("data/images/val")
        val_label_dir = Path("data/labels/val")

        if not val_img_dir.exists():
            pytest.skip("验证图像目录不存在")

        images = list(val_img_dir.glob("*.jpg")) + list(val_img_dir.glob("*.png"))
        for img_path in images:
            label_path = val_label_dir / f"{img_path.stem}.txt"
            # 标签文件可以不存在（无目标的图像）
            if label_path.exists():
                # 验证标签格式
                with label_path.open("r") as f:
                    lines = f.readlines()
                    for line in lines:
                        parts = line.strip().split()
                        assert len(parts) == 5, f"标签格式错误: {line}"
                        class_id = int(parts[0])
                        assert 0 <= class_id < 5, f"类别 ID 超出范围: {class_id}"


class TestModelLoading:
    """测试模型加载"""

    def test_load_best_model(self) -> None:
        """测试加载最佳模型"""
        best_pt = Path("runs/train/exp/weights/best.pt")
        if not best_pt.exists():
            pytest.skip("best.pt 不存在，跳过加载测试")

        from ultralytics import YOLO

        # 加载模型
        model = YOLO(str(best_pt))

        # 验证模型属性
        assert model is not None, "模型加载失败"
        assert hasattr(model, "names"), "模型缺少 names 属性"
        assert len(model.names) == 5, "模型类别数应为 5"

    def test_load_last_model(self) -> None:
        """测试加载最终模型"""
        last_pt = Path("runs/train/exp/weights/last.pt")
        if not last_pt.exists():
            pytest.skip("last.pt 不存在，跳过加载测试")

        from ultralytics import YOLO

        # 加载模型
        model = YOLO(str(last_pt))

        # 验证模型属性
        assert model is not None, "模型加载失败"
        assert hasattr(model, "names"), "模型缺少 names 属性"
        assert len(model.names) == 5, "模型类别数应为 5"

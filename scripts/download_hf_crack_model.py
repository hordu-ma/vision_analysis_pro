"""下载公开裂缝检测参考模型到本地 models/ 目录。"""

from pathlib import Path

from huggingface_hub import hf_hub_download


REPO_ID = "akar49/only-crack-I"
FILES = ["config.json", "preprocessor_config.json", "pytorch_model.bin"]


def main() -> None:
    target_dir = Path("models/only-crack-I")
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in FILES:
        path = hf_hub_download(repo_id=REPO_ID, filename=filename, local_dir=target_dir)
        print(path)


if __name__ == "__main__":
    main()

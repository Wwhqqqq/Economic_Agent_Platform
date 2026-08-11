"""Download Qwen2.5-7B-Instruct via ModelScope (China-friendly)."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-dir", required=True)
    args = parser.parse_args()
    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    try:
        from modelscope import snapshot_download
        path = snapshot_download(
            "Qwen/Qwen2.5-7B-Instruct",
            local_dir=str(local_dir),
            revision="master",
        )
        print("ModelScope OK:", path)
        return
    except Exception as e:
        print("ModelScope failed:", e)
        print("Fallback to HF mirror ...")

    import os
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from huggingface_hub import snapshot_download
    path = snapshot_download(
        repo_id="Qwen/Qwen2.5-7B-Instruct",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    print("HF mirror OK:", path)


if __name__ == "__main__":
    main()

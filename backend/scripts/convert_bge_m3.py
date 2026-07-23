"""把 bge-m3 的 pytorch_model.bin 转成 model.safetensors。

TEI 1.5+ 只支持 safetensors 格式，但 BAAI/bge-m3 仓库只有 pytorch_model.bin。
转换后可卸载 torch。

用法：
    cd backend
    python scripts/convert_bge_m3.py
"""
import os
from pathlib import Path

import torch
from safetensors.torch import save_file


def main() -> None:
    model_dir = Path("models/bge-m3")
    src = model_dir / "pytorch_model.bin"
    dst = model_dir / "model.safetensors"

    if dst.exists():
        print(f"✓ 已存在 {dst}，跳过转换")
        return

    if not src.exists():
        raise FileNotFoundError(f"未找到 {src}")

    print(f"加载 {src} ...")
    state_dict = torch.load(src, map_location="cpu", weights_only=True)

    # safetensors 要求 tensor 是 contiguous
    print("转换 tensor 为 contiguous ...")
    state_dict = {k: v.contiguous() for k, v in state_dict.items()}

    print(f"保存 {dst} ...")
    save_file(state_dict, str(dst))

    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"✓ 转换完成: {dst} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()

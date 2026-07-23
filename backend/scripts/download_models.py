"""下载 RAG 所需模型到 ./models 目录（hf-mirror 加速）。

模型清单：
  - BAAI/bge-m3            ~2.3GB  embedding（TEI + process 内 CrossEncoder 共用）
  - BAAI/bge-reranker-v2-m3 ~560MB reranker

用法：
    cd backend
    python scripts/download_models.py              # 下载全部
    python scripts/download_models.py --no-onnx    # 跳过 ONNX（仅用 safetensors 时）
    python scripts/download_models.py --list       # 仅查看目标路径与大小
"""
import argparse
import os
import sys
from pathlib import Path

# ===== 配置 =====
HF_ENDPOINT = "https://hf-mirror.com"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# 模型定义：repo_id → 本地目录名
MODELS = {
    "BAAI/bge-m3": "bge-m3",
    "BAAI/bge-reranker-v2-m3": "bge-reranker-v2-m3",
}

# 必要文件：权重 + tokenizer + config（跳过 README/图片/onnx 等冗余）
ALLOW_PATTERNS = [
    "*.safetensors",
    "config.json",
    "config_sentence_transformers.json",
    "sentence_bert_config.json",
    "modules.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "1_Pooling/*",
]

# ONNX 文件（可选，仅 process 内 ONNX Runtime 推理时需要）
ONNX_PATTERNS = ["onnx/*"]


def _set_env() -> None:
    """设置 hf-mirror 加速端点（必须在 import huggingface_hub 之前）。"""
    os.environ["HF_ENDPOINT"] = HF_ENDPOINT


def _check_model(path: Path) -> tuple[bool, str]:
    """检查模型目录是否已下载完整（含 safetensors 权重）。"""
    if not path.exists():
        return False, "目录不存在"
    safetensors = list(path.rglob("*.safetensors"))
    if not safetensors:
        return False, "缺少 safetensors 权重文件"
    tokenizer = path / "tokenizer.json"
    if not tokenizer.exists():
        return False, "缺少 tokenizer.json"
    return True, f"OK ({len(safetensors)} 个权重文件)"


def _dir_size(path: Path) -> str:
    """格式化目录大小。"""
    if not path.exists():
        return "0 MB"
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    if total >= 1024 ** 3:
        return f"{total / 1024 ** 3:.2f} GB"
    return f"{total / 1024 ** 2:.1f} MB"


def download_model(repo_id: str, local_name: str, include_onnx: bool) -> None:
    """下载单个模型到 MODELS_DIR / local_name。"""
    from huggingface_hub import snapshot_download

    target = MODELS_DIR / local_name
    ok, msg = _check_model(target)
    if ok:
        print(f"  [skip] {local_name} 已存在 ({_dir_size(target)}) — {msg}")
        return

    print(f"  [download] {repo_id} → {target}")
    patterns = ALLOW_PATTERNS + (ONNX_PATTERNS if include_onnx else [])
    print(f"  包含文件: {patterns}")
    if include_onnx:
        print(f"  含 ONNX: {ONNX_PATTERNS}")
    else:
        print(f"  跳过 ONNX（如需 ONNX 推理请去掉 --no-onnx）")

    path = snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        allow_patterns=patterns,
        resume_download=True,  # 断点续传
    )
    print(f"  [done] {local_name} ({_dir_size(target)}) — 下载到 {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 RAG 模型（bge-m3 + reranker）")
    parser.add_argument(
        "--no-onnx",
        action="store_true",
        help="跳过 ONNX 文件（仅用 safetensors 时指定）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出目标路径与状态，不下载",
    )
    args = parser.parse_args()

    _set_env()
    print(f"模型目录: {MODELS_DIR}")
    print(f"加速端点: {HF_ENDPOINT}")
    print()

    if args.list:
        for repo_id, local_name in MODELS.items():
            target = MODELS_DIR / local_name
            ok, msg = _check_model(target)
            status = "OK" if ok else "MISSING"
            print(f"  {local_name:30s} [{status}] {_dir_size(target):12s} {msg}")
        return 0

    for repo_id, local_name in MODELS.items():
        print(f"{'=' * 60}")
        print(f"模型: {repo_id}")
        print(f"{'=' * 60}")
        try:
            download_model(repo_id, local_name, include_onnx=not args.no_onnx)
        except Exception as e:
            print(f"  [ERROR] {repo_id} 下载失败: {e}", file=sys.stderr)
            return 1
        print()

    # 最终校验
    print(f"{'=' * 60}")
    print("下载完成，校验结果:")
    print(f"{'=' * 60}")
    all_ok = True
    for repo_id, local_name in MODELS.items():
        target = MODELS_DIR / local_name
        ok, msg = _check_model(target)
        status = "OK" if ok else "FAIL"
        print(f"  {local_name:30s} [{status}] {_dir_size(target):12s}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n全部模型就绪。可启动 TEI 服务或后端 reranker。")
        return 0
    else:
        print("\n部分模型缺失，请重新运行本脚本（支持断点续传）。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

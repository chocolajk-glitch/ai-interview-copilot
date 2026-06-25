"""手动测试 LLM 工厂：3 个 provider 各跑一次。"""
import sys
import io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.factory import chat, get_llm


def test_provider(provider: str) -> None:
    print(f"\n=== 测试 {provider} ===")
    try:
        llm = get_llm(provider)
        print(f"  Client 类型: {type(llm).__name__}")
        print(f"  Model: {getattr(llm, 'model', None) or getattr(llm, 'model_name', '?')}")
        reply = chat("用一句话介绍你自己", provider=provider)
        print(f"  回复: {reply[:120]}")
        print(f"  ✅ {provider} OK")
    except Exception as e:
        print(f"  ❌ {provider} 失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    for p in ["deepseek", "qwen", "minimax"]:
        test_provider(p)
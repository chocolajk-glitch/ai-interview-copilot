"""清库脚本：清除 Chroma 向量库 + BM25 索引 + processed 目录。

用法：
    python -m scripts.clear_index
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.logging import setup_logging, logger


def main():
    setup_logging()
    backend_root = Path(__file__).resolve().parent.parent

    # 1. 清除 Chroma 持久化文件
    chroma_dir = backend_root / "data" / "chroma"
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.info(f"已删除 {chroma_dir}")
    else:
        logger.info("Chroma 目录不存在，跳过")

    # 2. 清除 processed 目录
    processed_dir = backend_root / "data" / "processed"
    if processed_dir.exists():
        shutil.rmtree(processed_dir)
        logger.info(f"已删除 {processed_dir}")
    else:
        logger.info("processed 目录不存在，跳过")

    # 3. 清除 uploads 目录
    uploads_dir = backend_root / "data" / "uploads"
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)
        logger.info(f"已删除 {uploads_dir}")
    else:
        logger.info("uploads 目录不存在，跳过")

    # 4. 清除 SQLite 数据库
    db_path = backend_root / "data" / "interview.db"
    if db_path.exists():
        db_path.unlink()
        logger.info(f"已删除 {db_path}")
    else:
        logger.info("SQLite 数据库不存在，跳过")

    logger.info("清库完成")


if __name__ == "__main__":
    main()

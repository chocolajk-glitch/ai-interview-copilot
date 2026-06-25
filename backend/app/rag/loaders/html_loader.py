"""HTML 文档加载器：把 .html 文件读成 LangChain Document 对象。"""
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.documents import Document


def load_html(file_path: str | Path) -> Document:
    """加载单个 HTML 文件，提取正文文本。

    Args:
        file_path: HTML 文件路径

    Returns:
        单个 Document，内容为 HTML 正文纯文本
    """
    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # 移除 script / style 标签
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return Document(
        page_content=text,
        metadata={"source": str(file_path)},
    )


def load_html_docs(directory: str | Path) -> list[Document]:
    """加载目录下所有 .html 文件。"""
    directory = Path(directory)
    docs = []
    for html_path in directory.glob("**/*.html"):
        docs.append(load_html(html_path))
    return docs

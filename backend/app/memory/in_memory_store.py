from collections import defaultdict

from langchain_core.messages import BaseMessage

from app.memory.chat_history_store import ChatHistoryStore


class InMemoryChatHistoryStore(ChatHistoryStore):
    def __init__(self):
        self._store: dict[str, list[BaseMessage]] = defaultdict(list)

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        return list(self._store.get(session_id, []))

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        self._store[session_id].append(message)

    def clear(self, session_id: str) -> None:
        self._store[session_id] = []
from abc import ABC, abstractmethod

from langchain_core.messages import BaseMessage


class ChatHistoryStore(ABC):
    @abstractmethod
    def get_messages(self, session_id: str) -> list[BaseMessage]:
        ...

    @abstractmethod
    def add_message(self, session_id: str, message: BaseMessage) -> None:
        ...

    @abstractmethod
    def clear(self, session_id: str) -> None:
        ...
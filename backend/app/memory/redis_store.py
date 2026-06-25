import json

import redis
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.memory.chat_history_store import ChatHistoryStore


def _serialize(msg: BaseMessage) -> str:
    return json.dumps({"type": msg.type, "content": msg.content}, ensure_ascii=False)


def _deserialize(data: str) -> BaseMessage:
    obj = json.loads(data)
    t = obj["type"]
    content = obj["content"]
    if t == "human":
        return HumanMessage(content=content)
    if t == "ai":
        return AIMessage(content=content)
    if t == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


class RedisChatHistoryStore(ChatHistoryStore):
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, ttl: int = 86400):
        self._r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._ttl = ttl

    def _key(self, session_id: str) -> str:
        return f"chat_history:{session_id}"

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        items = self._r.lrange(self._key(session_id), 0, -1)
        return [_deserialize(x) for x in items]

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        key = self._key(session_id)
        self._r.rpush(key, _serialize(message))
        self._r.expire(key, self._ttl)

    def clear(self, session_id: str) -> None:
        self._r.delete(self._key(session_id))
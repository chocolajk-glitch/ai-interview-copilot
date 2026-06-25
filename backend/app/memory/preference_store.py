"""长期用户偏好存储：记住用户的模型偏好、关注领域等。"""
from app.core.config import settings


class UserPreferenceStore:
    """用户偏好存储接口（内存实现，可扩展为 Redis/DB）。"""

    def __init__(self):
        self._prefs: dict[str, dict] = {}  # session_id → prefs

    def get(self, session_id: str) -> dict:
        """获取用户偏好。"""
        return self._prefs.get(session_id, {})

    def set(self, session_id: str, key: str, value: str) -> None:
        """设置单个偏好。"""
        if session_id not in self._prefs:
            self._prefs[session_id] = {}
        self._prefs[session_id][key] = value

    def update(self, session_id: str, prefs: dict) -> None:
        """批量更新偏好。"""
        if session_id not in self._prefs:
            self._prefs[session_id] = {}
        self._prefs[session_id].update(prefs)

    def delete(self, session_id: str) -> None:
        """删除用户偏好。"""
        self._prefs.pop(session_id, None)


_store: UserPreferenceStore | None = None


def get_preference_store() -> UserPreferenceStore:
    global _store
    if _store is None:
        _store = UserPreferenceStore()
    return _store

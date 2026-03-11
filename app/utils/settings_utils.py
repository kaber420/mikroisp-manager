from app.db.engine_sync import get_sync_session
from app.models.setting import Setting


def get_setting_sync(key: str) -> str | None:
    """
    Helper function to get a setting value synchronously.
    Uses a temporary sync session.
    """
    with next(get_sync_session()) as session:
        setting = session.get(Setting, key)
        return setting.value if setting else None

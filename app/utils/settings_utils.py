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
def set_setting_sync(key: str, value: str):
    """
    Helper function to set a setting value synchronously.
    """
    with next(get_sync_session()) as session:
        setting = session.get(Setting, key)
        if setting:
            setting.value = value
            session.add(setting)
        else:
            new_setting = Setting(key=key, value=value)
            session.add(new_setting)
        session.commit()

from typing import Dict
from sqlmodel import Session, select
from ..models.setting import Setting

class SettingsService:
    def __init__(self, session: Session):
        self.session = session

    def get_all_settings(self) -> Dict[str, str]:
        settings = self.session.exec(select(Setting)).all()
        return {s.key: s.value for s in settings}

    def update_settings(self, settings_to_update: Dict[str, str]):
        for key, value in settings_to_update.items():
            setting = self.session.get(Setting, key)
            if setting:
                setting.value = value
                self.session.add(setting)
            else:
                # If setting doesn't exist, create it (optional, but good for robustness)
                new_setting = Setting(key=key, value=value)
                self.session.add(new_setting)
        
        self.session.commit()

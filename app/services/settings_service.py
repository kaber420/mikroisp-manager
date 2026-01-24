from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.setting import Setting


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_settings(self) -> dict[str, str]:
        result = await self.session.execute(select(Setting))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}

    async def update_settings(self, settings_to_update: dict[str, str]):
        for key, value in settings_to_update.items():
            setting = await self.session.get(Setting, key)
            if setting:
                setting.value = value
                self.session.add(setting)
            else:
                # If setting doesn't exist, create it (optional, but good for robustness)
                new_setting = Setting(key=key, value=value)
                self.session.add(new_setting)

        await self.session.commit()

    async def get_setting_value(self, key: str) -> str | None:
        setting = await self.session.get(Setting, key)
        return setting.value if setting else None

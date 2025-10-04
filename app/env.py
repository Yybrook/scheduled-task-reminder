from pydantic_settings import BaseSettings, SettingsConfigDict
import os

dir_name = os.path.dirname(__file__)
father_dir_name = os.path.dirname(dir_name)
env_path = os.path.join(father_dir_name, ".env")


class Settings(BaseSettings):
    SMTP_SERVER: str
    SMTP_PORT: int = 465
    SMTP_USER: str
    SMTP_PASSWORD: str

    SQL_HOST: str
    SQL_PORT: int = 3306
    SQL_USER: str
    SQL_PASSWORD: str
    SQL_DATABASE: str

    model_config = SettingsConfigDict(env_file=env_path)

settings = Settings()


if __name__ == "__main__":
    print(settings)
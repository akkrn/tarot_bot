from dataclasses import dataclass

from environs import Env


@dataclass
class Proxy:
    path: int

@dataclass
class FilesPaths:
    images_path: str


@dataclass
class PromtStorage:
    user_3_card_promt: str
    user_1_card_promt: str
    max_tokens: int


@dataclass
class RedisClient:  # TODO прописать нормальные значения для соединения с Redis
    port: int
    user: str
    password: str
    host: str


@dataclass
class AdminRights:
    owner_id: int
    admins_ids: list[int]


@dataclass
class OpenAIConfig:
    api_key: str


@dataclass
class Sentry:
    url: str


@dataclass
class DatabaseConfig:
    postgres_db: str
    db_host: str
    postgres_user: str
    postgres_password: str
    db_port: int


@dataclass
class TgBot:
    token: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig
    openai: OpenAIConfig
    sentry: Sentry
    admin_rights: AdminRights
    redis_client: RedisClient
    promt_storage: PromtStorage
    files_paths: FilesPaths
    proxy: Proxy


def load_config(path: str | None) -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(token=env("BOT_TOKEN")),
        db=DatabaseConfig(
            postgres_db=env("POSTGRES_DB"),
            db_host=env("DB_HOST"),
            postgres_user=env("POSTGRES_USER"),
            postgres_password=env("POSTGRES_PASSWORD"),
            db_port=env.int("DB_PORT"),
        ),
        openai=OpenAIConfig(api_key=env("OPENAI_API_KEY")),
        sentry=Sentry(url=env("SENTRY_URL")),
        admin_rights=AdminRights(
            owner_id=env.int("OWNER_ID"), admins_ids=env.list("ADMINS_IDS")
        ),
        redis_client=RedisClient(
            port=env.int("REDIS_PORT"),
            user=env("REDIS_USER"),
            password=env("REDIS_PASSWORD"),
            host=env("REDIS_HOST"),
        ),
        promt_storage=PromtStorage(
            user_1_card_promt=env.str("USER_1_CARD_PROMT"),
            user_3_card_promt=env.str("USER_3_CARD_PROMT"),
            max_tokens=env.str("MAX_TOKENS"),
        ),
        files_paths=FilesPaths(images_path=env.str("IMAGES_PATH")),
        proxy=Proxy(path=env.str("PROXY_PATH"))
    )

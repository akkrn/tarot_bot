import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config_data.config import load_config

config = load_config(path=None)

# Database connection
db_name = config.db.postgres_db
db_user = config.db.postgres_user
db_password = config.db.postgres_password
db_host = config.db.db_host
db_port = config.db.db_port

database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_async_engine(database_url, echo=False)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# Redis connection
redis_password = config.redis_client.password
redis_client = redis.Redis(
    password=redis_password,
)

# Monitoring & Exceptions
sentry_url = config.sentry.url

# Telegram IDs
owner_id = config.admin_rights.owner_id
admins_ids = [int(x) for x in config.admin_rights.admins_ids]

# OpenAI Config
openai_api_key = config.openai.api_key
openai_engine = config.openai.engine

# DeepSeek Config
deepseek_api_key = config.deepseek.api_key
deepseek_engine = config.deepseek.engine


user_1_card_promt = config.promt_storage.user_1_card_promt
user_3_card_promt = config.promt_storage.user_3_card_promt
max_tokens = int(config.promt_storage.max_tokens)


# Files Paths
images_path = config.files_paths.images_path

# Payments Token
payments_provider_token = config.payment.provider_token

# Proxy
proxy_path = config.proxy.path

# Telegram Bot
bot = Bot(
    token=config.tg_bot.token,
    default=DefaultBotProperties(parse_mode="Markdown"),
)
storage = RedisStorage(redis=redis_client)
dp = Dispatcher(storage=storage)

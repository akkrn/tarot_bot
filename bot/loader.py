from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
from aiogram.fsm.storage.redis import RedisStorage

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
redis_client = redis.Redis()
# redis_client = redis.from_url("redis://LOGIN:PASSWORD@HOST:PORT/NUM_DB")

# Monitoring & Exceptions
sentry_url = config.sentry.url

# Telegram IDs
owner_id = config.admin_rights.owner_id
admins_ids = [int(x) for x in config.admin_rights.admins_ids]

# OpenAI Config
openai_api_key = config.openai.api_key
user_1_card_promt = config.promt_storage.user_1_card_promt
user_3_card_promt = config.promt_storage.user_3_card_promt
max_tokens = int(config.promt_storage.max_tokens)


# Files Paths
images_path = config.files_paths.images_path

# Telegram Bot
bot = Bot(
    token=config.tg_bot.token,
    default=DefaultBotProperties(parse_mode="Markdown"),
)
storage = RedisStorage(redis=redis_client)
dp = Dispatcher(storage=storage)

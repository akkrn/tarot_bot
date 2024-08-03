from loader import redis_client as redis


async def save_file_id(key: str, file_id: str):
    await redis.set(key, file_id)


async def get_file_id(key: str) -> str:
    return await redis.get(key)


async def delete_file_id(key: str) -> str:
    return await redis.delete(key)

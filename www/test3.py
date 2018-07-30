import asyncio
from aiomysql import create_pool
loop = asyncio.get_event_loop()
async def go():
    async with create_pool(host='localhost', port=3306,
                           user='www-data', password='www-data',
                           db='awesome', loop=loop) as pool:
        async with pool.get() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 42;")
                value = await cur.fetchone()
                print(value)
loop.run_until_complete(go())
import aiohttp
from loguru import logger


async def get_text(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        logger.debug(url)
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()


async def test_url(url: str, raise_for_status: bool = True) -> bool:
    async with aiohttp.ClientSession() as session:
        logger.debug(url)
        async with session.head(url, allow_redirects=True) as resp:
            if raise_for_status:
                resp.raise_for_status()
            return resp.ok

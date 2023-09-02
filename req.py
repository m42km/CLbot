import aiohttp

session = aiohttp.ClientSession()

async def requestGET(url: str) -> dict:
    resp = await session.get(url)
    json = await resp.json()
    return json

async def requestPOST(rSession: aiohttp.ClientSession, url: str, data: dict):
    resp = await rSession.post(url, data=data)
    return resp

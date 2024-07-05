import aiohttp

async def requestGET(url: str) -> dict:
    session = aiohttp.ClientSession()
    resp = await session.get(url)
    json = await resp.json()
    return json

async def requestPOST(rSession: aiohttp.ClientSession, url: str, data: dict):
    resp = await rSession.post(url, data=data)
    # we don't need json or much data from POST requests here, so just return the response
    return resp

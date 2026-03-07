import asyncio, websockets, pyautogui, json, ssl
from aiohttp import web

pyautogui.PAUSE = 0
pressed = set()

def press(key):
    if key not in pressed:
        pyautogui.keyDown(key); pressed.add(key)

def release(key):
    if key in pressed:
        pyautogui.keyUp(key); pressed.discard(key)

async def handler(ws):
    print("Phone connected!")
    async for msg in ws:
        data = json.loads(msg)
        pitch = data.get('beta', 0)
        roll  = data.get('gamma', 0)
        T = 12
        if pitch > T:   press('w')
        else:           release('w')
        if pitch < -T:  press('s')
        else:           release('s')
        if roll < -T:   press('a')
        else:           release('a')
        if roll > T:    press('d')
        else:           release('d')

async def dummy_http(request):
    return web.Response(text="OK - cert trusted!")

async def main():
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain('cert.pem', 'key.pem')

    # Dummy HTTP page so iPhone can trust the cert
    app = web.Application()
    app.router.add_get('/', dummy_http)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8766, ssl_context=ssl_ctx)
    await site.start()
    print("Visit https://10.90.221.253:8766 on iPhone to trust cert")

    # Actual WebSocket server
    print("Waiting for phone...")
    async with websockets.serve(handler, "0.0.0.0", 8765, ssl=ssl_ctx):
        await asyncio.Future()

asyncio.run(main())
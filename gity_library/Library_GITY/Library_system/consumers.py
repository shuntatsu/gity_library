import time
from channels.generic.websocket import AsyncWebsocketConsumer

class YourConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        while True:
            # 3秒ごとにビュー関数を呼び出す処理
            await self.send(text_data="Calling your view function...")
            time.sleep(3)

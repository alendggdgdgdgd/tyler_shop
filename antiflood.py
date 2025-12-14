import time
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit=1.5):
        super().__init__()
        self.limit = limit
        self.last_time = {}

    async def on_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id
        now = time.time()

        if user_id in self.last_time:
            if now - self.last_time[user_id] < self.limit:
                await message.answer("⛔ Не спамь, подожди немного")
                raise CancelHandler()

        self.last_time[user_id] = now
from telegram.ext import Updater

import config

class TelegramBot:
    def __init__(self):
        self.updater = Updater(config.TG_API)
    
    def send_msg(self, text):
        self.updater.bot.send_message(chat_id=config.TG_ID, text=text)
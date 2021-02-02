from telegram.ext import Updater
from telegram.ext import CommandHandler

import config

class TelegramBot:
    def __init__(self):
        self.updater = Updater(config.TG_API)
        # self.updater = Updater(config.TG_TEST_API)
        self.dispatcher = self.updater.dispatcher

        self.stop_handler = CommandHandler('stop', self.stop)
        self.start_handler = CommandHandler('restart', self.restart)

        self.dispatcher.add_handler(self.stop_handler)
        self.dispatcher.add_handler(self.start_handler)
        self.is_stopped = False

        self.updater.start_polling()
    
    def send_msg(self, text):
        self.updater.bot.send_message(chat_id=config.TG_ID, text=text)

    def stop(self, update, context):
        self.is_stopped = True
        context.bot.send_message(chat_id=config.TG_ID, text='[Alarm] All stopped')
        
    def restart(self, update, context):
        self.is_stopped = False
        context.bot.send_message(chat_id=config.TG_ID, text='[Alarm] All restarted')
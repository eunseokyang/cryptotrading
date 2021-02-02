import time
import json
import websocket

import alarm
import config

SOCKET = "wss://fstream.binance.com/ws/btcusdt@kline_1m"

telebot = alarm.TelegramBot(config.TG_TEST_API, config.TG_ID)

def on_open(ws):
    print("opened connection")

def on_close(ws):
    print("closed connection")

def on_message(ws, message):
    if telebot.is_stopped == False:
        json_message = json.loads(message)

        # if abs(time.time() - json_message["E"]/1000) < 2:
        #     telebot.send_msg(json_message)
        #     time.sleep(1)

        telebot.send_msg(json_message)
        telebot.send_msg(time.time())
        time.sleep(1)

ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
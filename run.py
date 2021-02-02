import time
import json
import websocket

import alarm
import trade
import config

SOCKET = "wss://fstream.binance.com/ws/btcusdt@kline_5m"

telebot = alarm.TelegramBot(config.TG_API, config.TG_ID)
bn = trade.Trade(telebot)

def on_open(ws):
    print("opened connection")

def on_close(ws):
    print("closed connection")

def on_message(ws, message):
    if telebot.is_stopped == False:
        json_message = json.loads(message)
        if abs(time.time() - json_message["E"]/1000) < 2:
            bn.run(json_message)

ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
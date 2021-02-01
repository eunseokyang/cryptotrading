import json
import websocket

import alarm
import trade

SOCKET = "wss://fstream.binance.com/ws/btcusdt@kline_5m"

telebot = alarm.TelegramBot()
bn = trade.Trade(telebot)


def on_open(ws):
    print("opened connection")

def on_close(ws):
    print("closed connection")

def on_message(ws, message):
    json_message = json.loads(message)
    bn.run(json_message)

ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
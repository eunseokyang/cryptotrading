import time

import talib
import numpy as np

from binance.enums import *
from binance.client import Client

import util
import config

RSI_PERIOD = 14
RSI_OVERBOUGHT = 60
RSI_OVERSOLD = 40
RSI_MID = 50
SYMBOL = 'BTCUSDT'
LEVERAGE = 1
LOSS_CUT = 0.01
MAX_CLOSE_LENGTH = 500
ALERT_THRESHOLD = 0.15

class Trade:
    def __init__(self, telebot):
        self.telebot = telebot
        self.client = Client(config.BN_API_KEY, config.BN_API_SECRET)

        # binance client setting
        self.client.futures_change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
        if self.client.futures_get_position_mode()['dualSidePosition'] == True:
            self.client.futures_change_position_mode(dualSidePosition="false")

        # initial balance check
        self.check_balance()
        self.initial_balance = self.balance

        print(f'initial balance: ${self.initial_balance}')

        # alert stop
        self.alert_stop = False

        self.is_closed_initialized = False
        self.closes = [] 
        self.curr_rsi = 0
        self.prev_rsi = 0       

        self.half_open = False
        self.last_opening_order_time = 0

    def check_balance(self):
        balances = self.client.futures_account_balance()
        self.balance = float(next(item['balance'] for item in balances if item['asset'] == 'USDT'))

    def check_alert_stop(self):
        profit = (self.balance - self.initial_balance) / self.initial_balance
        if profit < -ALERT_THRESHOLD:
            self.telebot.send_msg('[ALERT] all stopped')
            self.alert_stop = True

    def get_currunt_position(self):
        for item in self.client.futures_position_information():
            if (item['symbol'] == 'BTCUSDT') and (item['positionSide'] == 'BOTH'):
                self.curr_position = item
        self.position_amount = float(self.curr_position['positionAmt'])
        self.entry_price = float(self.curr_position['entryPrice'])
        self.mark_price = float(self.curr_position['markPrice'])

    def cancel_open_orders(self):
        try:
            self.client.futures_cancel_all_open_orders(symbol=SYMBOL)
        except Exception as e:
            print(e)
            self.telebot.send_msg('[Error] Failed to cancel orders')

    def stop_market(self, symbol, stop_side, stop_order_type, stop_price, qty):
        stopPrice = "{:0.0{}f}".format(stop_price, 2)
        quantity = "{:0.0{}f}".format(qty, 3)

        try:
            self.client.futures_create_order(
                symbol=symbol,
                side=stop_side,
                type=stop_order_type,
                quantity=quantity,
                stopPrice=stopPrice
            )
            return True
        except Exception as e:
            print(e)
            self.telebot.send_msg(f"[Error] Stopping market error!")

    def open_order(self, symbol, side, order_type, msg):
        # update USDT balance
        self.check_balance()

        # 0.99 to care of delay
        qty = self.balance / self.mark_price * 0.99
        qty = util.round_down(qty, 3)  
        quantity = "{:0.0{}f}".format(qty, 3)
        
        try:
            print(f"[Open] {msg} ${qty*self.mark_price}, quantity: {quantity}, curr: {self.mark_price}")
            self.telebot.send_msg(f"[Open] {msg} ${qty*self.mark_price}, quantity: {quantity}, curr: {self.mark_price}")
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
            )

            self.last_opening_order_time = order["updateTime"] / 1000
            self.half_open = False

            self.get_currunt_position()
            self.check_balance()
            return True

        except Exception as e:
            print(e)
            self.telebot.send_msg(f"[Error] Opening order error!")
            return False

    def close_order(self, symbol, side, order_type, qty):
        quantity = "{:0.0{}f}".format(qty, 3)
        try:
            print(f"[Close] {side} ${qty*self.mark_price}, quantity: {quantity}, curr: {self.mark_price}")
            self.telebot.send_msg(f"[Close] {side} ${qty*self.mark_price}, quantity: {quantity}, curr: {self.mark_price}")

            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity
            )
            print(order)

            self.get_currunt_position()
            self.check_balance()

            # When all position is closed, check ALERT STOP.
            if self.position_amount == 0:
                self.check_alert_stop()

            return True

        except Exception as e:
            print(e)
            self.telebot.send_msg(f"[Error] Closing order error!")
            return False

    def judge(self):
        # not in position
        if self.position_amount == 0:
            if (self.prev_rsi >= RSI_OVERBOUGHT) and (self.curr_rsi < RSI_OVERBOUGHT):
                print('buy short')
                self.open_order(SYMBOL, SIDE_SELL, "MARKET", "SHORT")
                self.stop_market(SYMBOL, SIDE_BUY, "STOP_MARKET", self.entry_price * (1 + LOSS_CUT), -self.position_amount)
            elif (self.prev_rsi <= RSI_OVERSOLD) and (self.curr_rsi > RSI_OVERSOLD):
                print('buy long')
                self.open_order(SYMBOL, SIDE_BUY, "MARKET", "LONG")
                self.stop_market(SYMBOL, SIDE_SELL, "STOP_MARKET", self.entry_price * (1 - LOSS_CUT), self.position_amount)
        # long position
        elif self.position_amount > 0:
            # full open
            if self.half_open == False:
                if self.curr_rsi >= RSI_MID:
                    self.close_order(SYMBOL, SIDE_SELL, "MARKET", self.position_amount / 2)
                    self.cancel_open_orders()
                    self.stop_market(SYMBOL, SIDE_SELL, "STOP_MARKET", self.entry_price * (1 - LOSS_CUT), self.position_amount)
                    self.half_open = True
            # half open
            else:
                if self.curr_rsi >= RSI_OVERBOUGHT:
                    self.close_order(SYMBOL, SIDE_SELL, "MARKET", self.position_amount)
                    self.cancel_open_orders()
                    self.half_open = False
        # short position
        elif self.position_amount < 0:
            # full open
            if self.half_open == False:
                if self.curr_rsi <= RSI_MID:
                    self.close_order(SYMBOL, SIDE_BUY, "MARKET", -self.position_amount / 2)
                    self.cancel_open_orders()
                    self.stop_market(SYMBOL, SIDE_BUY, "STOP_MARKET", self.entry_price * (1 + LOSS_CUT), -self.position_amount)
                    self.half_open = True
            # half open
            else:
                if self.curr_rsi <= RSI_OVERSOLD:
                    self.close_order(SYMBOL, SIDE_BUY, "MARKET", -self.position_amount)
                    self.cancel_open_orders()
                    self.half_open = False

    def manage_risk(self):
        now = time.time()
        if (self.position_amount > 0) and (now - self.last_opening_order_time > 45*60):
            if (self.mark_price - self.entry_price) / self.entry_price < 0.01:
                print('close long position due to low profit')
                self.close_order(SYMBOL, SIDE_SELL, "MARKET", self.position_amount)
                self.cancel_open_orders()

        elif (self.position_amount < 0) and (now - self.last_opening_order_time > 45*60):
            if (self.entry_price - self.mark_price) / self.entry_price < 0.01:
                print('close short position due to low profit')
                self.close_order(SYMBOL, SIDE_BUY, "MARKET", -self.position_amount)
                self.cancel_open_orders()

    def initialize_rsi(self, time_last):
        # 1 min or 5 mins
        candles = self.client.futures_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_5MINUTE)
        self.closes = [float(candle[4]) for candle in candles]
        close_time_last = int(candles[-1][0])

        print(f'prev_close_time: {close_time_last}, websocket_close_time: {time_last}')

        # 1 min or 5 mins
        if time_last == close_time_last:
            self.closes = self.closes[:-1]
        elif close_time_last - time_last == 5*60*1000:
            self.closes = self.closes[:-2]
        else:
            self.telebot.send_msg('websocket sync error')
        
        self.is_closed_initialized = True

    def get_rsi(self, price_info):
        candle = price_info['k']
        is_candle_closed = candle['x']
        close = float(candle['c'])
        
        if is_candle_closed:
            if self.is_closed_initialized == False:
                time_last = int(candle['t'])
                self.initialize_rsi(time_last)

            self.closes.append(close)
            self.closes = self.closes[-MAX_CLOSE_LENGTH:]

            rsi = talib.RSI(np.array(self.closes), timeperiod=RSI_PERIOD)

            self.curr_rsi, self.prev_rsi = rsi[-1], rsi[-2]
            print(f"RSI: {self.curr_rsi:.2f}")      
            return True

        return False

    def run(self, price_info):
        if not self.alert_stop:
            self.get_currunt_position()
            self.manage_risk()
            if self.get_rsi(price_info):
                self.judge()
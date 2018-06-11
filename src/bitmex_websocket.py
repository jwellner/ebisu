# coding: UTF-8

import json
import threading

import websocket
from datetime import datetime

from src import logger, to_data_frame


class BitMexWs:
    # 稼働状態
    is_running = True
    # 通知先リスナー
    handlers = {}
    
    def __init__(self, test=False):
        """
        コンストラクタ
        """
        if test:
            domain = 'testnet.bitmex.com'
        else:
            domain = 'www.bitmex.com'
        endpoint = 'wss://' + domain + '/realtime?subscribe=tradeBin1m:XBTUSD,' \
                        'tradeBin5m:XBTUSD,tradeBin1h:XBTUSD,tradeBin1d:XBTUSD,instrument:XBTUSD'
        self.ws = websocket.WebSocketApp(endpoint,
                             on_message=self.__on_message,
                             on_error=self.__on_error,
                             on_close=self.__on_close)
        self.wst = threading.Thread(target=self.__start)
        self.wst.daemon = True
        self.wst.start()
        
    def __start(self):
        """
        WebSocketを開始する
        """
        self.ws.run_forever()
        while self.is_running:
            pass

    def __on_error(self, ws, message):
        """
        WebSokcetでエラーが発生した場合
        :param ws:
        :param message:
        """
        logger.error(message)

    def __on_message(self, ws, message):
        """
        新しいデータを取得した場合
        :param ws:
        :param message:
        :return:
        """
        try:
            object = json.loads(message)
            if 'table' in object:
                if len(object['data']) <= 0:
                    return

                table = object['table']
                data = object['data'][0]

                if table.startswith("tradeBin"):
                    data['timestamp'] = datetime.strptime(data['timestamp'][:-5], '%Y-%m-%dT%H:%M:%S')
                    self.__emit(table, to_data_frame([data]))

                elif table.startswith("instrument"):
                    if 'lastPrice' in data:
                        data = data['lastPrice']
                        self.__emit(table, data)

        except Exception as e:
            logger.error(e)

    def __emit(self, key, value):
        """
        データを送る
        """
        if key in self.handlers:
            self.handlers[key](value)

    def __on_close(self, ws):
        """
        クローズした場合
        :param ws:
        """
        if 'close' in self.handlers:
            self.handlers['close']()
        
    def on_close(self, func):
        """
        クローズの通知先を登録する。
        :param func:
        """
        self.handlers['close'] = func
        
    def on_update(self, key, func):
        """
        新しいデータの通知先を登録する。
        :param key:
        :param func:
        """
        if key == '1m':
            self.handlers['tradeBin1m'] = func
        if key == '5m':
            self.handlers['tradeBin5m'] = func
        if key == '1h':
            self.handlers['tradeBin1h'] = func
        if key == '1d':
            self.handlers['tradeBin1d'] = func
        if key == 'price':
            self.handlers['instrument'] = func
    
    def close(self):
        """
        クローズする。
        """
        self.is_running = False
        self.ws.close()
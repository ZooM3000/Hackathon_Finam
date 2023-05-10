import backtrader as bt
import time
from datetime import datetime, timedelta, time #, time
from pytz import timezone
import requests


class Buy_Sell(bt.Strategy):
    """
    Стратегия для купли продажи на минутных барах для проверки инфраструктуры
    """

    def log(self, txt, dt=None):
        """Вывод строки с датой на консоль"""
        dt = bt.num2date(self.datas[0].datetime[0]) if not dt else dt  # Заданная дата или дата текущего бара
        print(f'{dt.strftime("%d.%m.%Y %H:%M")}, {txt}')  # Выводим дату и время с заданным текстом на консоль


    def log_telegram(self, txt):
        """Вывод строки с датой в телеграмм"""
        try:
            request = requests.get(f'https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={txt}')
        except requests.exceptions.RequestException as e:
            print(f"[Telegram] Can't send the message: {e}")


    def __init__(self, TELEGRAM_TOKEN, CHAT_ID, Path):
        """Инициализация торговой системы"""
        print('init')
        self.TELEGRAM_TOKEN = TELEGRAM_TOKEN
        self.CHAT_ID = CHAT_ID
        self.Path = Path

        self.DataClose = self.datas[0].close
        self.price = 0.0


    def next(self):

        timeOpen = bt.num2date(self.datas[0].datetime[0])
        if timeOpen.time() <= time(10, 1):
            return 
        delta = bt.num2date(self.datas[0].datetime[0]) - bt.num2date(self.datas[0].datetime[-1])
        timeNextClose = timeOpen + delta * 1.1 
        timeMarketNow = datetime.now()  # Текущее биржевое время

        if timeNextClose > timeMarketNow: #
            if time(10, 1) < timeMarketNow.time() < time(23, 50):
            
                self.log(f'DataClose = {self.DataClose[0]}')
            
                pos_2 = self.getposition(self.datas[0])
                print('pos_2 =', pos_2)
                
                if not self.getposition(self.datas[0]):
                    order = self.buy(exectype=bt.Order.Market)
                    self.log_telegram('BUY') 
                
                else:
                    order = self.sell(exectype=bt.Order.Market)
                    self.log_telegram('SELL') 
                


    
    
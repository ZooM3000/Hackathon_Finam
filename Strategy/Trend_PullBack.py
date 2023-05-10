from datetime import datetime
import backtrader as bt
import time
from datetime import datetime, timedelta, time
from pytz import timezone
import requests


class Trend_PullBack(bt.Strategy):
    """Покупаем по тренду на откате, не более одной сделки в день,
        выход по трейлинг стопу, 2 атр величина стопа
    """
    params = (
        ('Trend', 230),
        ('PullBack', 4)
    )


    def log(self, txt, dt=None):
        """Вывод строки с датой на консоль"""
        dt = bt.num2date(self.datas[0].datetime[0]) if dt is None else dt # Заданная дата или дата текущего бара
        print(f'{dt.strftime("%d.%m.%Y %H:%M")}, {txt}')  # Выводим дату и время с заданным текстом на консоль


    def log_telegram(self, txt):
        """Вывод строки с датой в телеграмм"""
        try:
            request = requests.get(f'https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={txt}')
        except requests.exceptions.RequestException as e:
            print(f"[Telegram] Can't send the message: {e}")


    def __init__(self, TELEGRAM_TOKEN, CHAT_ID, Path):
        """Инициализация торговой системы"""
        self.TELEGRAM_TOKEN = TELEGRAM_TOKEN
        self.CHAT_ID = CHAT_ID
        self.Path = Path

        self.DataClose = self.datas[0].close
        self.Trend  = bt.ind.SMA(self.DataClose, period = self.p.Trend)
        self.PullBack= bt.ind.Lowest(self.data, period=self.p.PullBack, plot=True, subplot=False)
        self.atr = bt.ind.ATR (period = 14)
        self.price = 0.0

        with open(f'{self.Path}Counter.txt', "r") as f:
            self.Counter = int(f.read()) #счетчик сделок, не больше одной в день

        self.order = None  # Заявка


    def next(self):
        """Получение следующего исторического/нового бара"""

        timeOpen = bt.num2date(self.datas[0].datetime[0])
        if timeOpen.time() <= time(10, 1):
            return 
        delta = bt.num2date(self.datas[0].datetime[0]) - bt.num2date(self.datas[0].datetime[-1])
        timeNextClose = timeOpen + delta * 1.1
        timeMarketNow = datetime.now()  # Текущее биржевое время

        if timeNextClose > timeMarketNow: #
            if time(10, 1) < timeMarketNow.time() < time(23, 50):
                
                if bt.num2date(self.datas[0].datetime[0]).date() != bt.num2date(self.datas[0].datetime[-1]).date():
                    self.Counter = 0
                    with open(f'{self.Path}Counter.txt', "w") as f:
                        f.write(str(self.Counter))

                self.stop_price = self.DataClose - 2.0 * self.atr

                if not self.getposition(self.datas[0]):
                #цена закрылась выше скользящцей покупаем
                    if self.DataClose > self.Trend :  
                        #цены ниже отката
                        if self.DataClose < self.PullBack[-1]: 
                            #счетчик сделок в день
                            if self.Counter == 0:
                                self.order = self.buy(exectype=bt.Order.Market)  # Рыночная заявка на покупку
                                self.Counter = self.Counter + 1 
                                with open(f'{self.Path}Counter.txt', "w") as f:
                                    f.write(str(self.Counter))
                                self.log_telegram('BUY')

                else:
                    #цена закрылась ниже линии стопа
                    if self.DataClose < self.stop_price:
                        self.order = self.sell(exectype=bt.Order.Market)  # Рыночная заявка на продажу
                        self.log_telegram('SELL')
                

        

        



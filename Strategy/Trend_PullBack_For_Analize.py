from datetime import datetime
import backtrader as bt


class Trend_PullBack_Analyze(bt.Strategy):
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

    def __init__(self):
        """Инициализация торговой системы"""
        self.DataClose = self.datas[0].close
        self.Trend  = bt.ind.SMA(self.DataClose, period = self.p.Trend)
        self.PullBack= bt.ind.Lowest(self.data, period=self.p.PullBack, plot=True, subplot=False)
        self.atr = bt.ind.ATR (period = 14)
        self.price = 0.0
        self.Counter = 0 #счетчик сделок, не больше одной в день

        self.order = None  # Заявка

    def next(self):
        """Получение следующего исторического/нового бара"""

        if bt.num2date(self.datas[0].datetime[0]).date() != bt.num2date(self.datas[0].datetime[-1]).date():
            self.Counter = 0


        if not self.position:
        # Цена закрылась выше скользящцей покупаем
            if self.DataClose > self.Trend :  
                #цены ниже отката
                if self.DataClose < self.PullBack[-1]: 
                    #счетчик сделок в день
                    if self.Counter == 0:
                        self.order = self.buy(exectype=bt.Order.Market)  # Рыночная заявка на покупку
                        self.price = self.DataClose[0] - 2.0 * self.atr[0]
                        self.order_2 = self.sell(exectype=bt.Order.Stop, price = self.price) 
                        self.Counter = self.Counter + 1 

        else:
            
            if self.DataClose[0] > self.DataClose[-1]:  # Если пришла заявка на продажу
                self.cancel(self.order_2)
                self.price = self.DataClose[0] - 2.0 * self.atr[0]
                self.order_2 = self.sell(exectype=bt.Order.Stop, price = self.price) 

        



import finam
from datetime import datetime, timedelta
import pytz
import time
from threading import Thread
import backtrader as bt
from BackTraderFinam import FNStore, FNBroker
from Config import Config
from FinamPy import FinamPy
import requests

from Strategy.Buy_Sell import Buy_Sell
from Strategy.Trend_PullBack import Trend_PullBack


#поток для запуска бэктрейдера
class Cerebro_worker(Thread):
    
    def __init__(self, Ticker, mode, Strategy, **kwargs):
        super().__init__()
        self.Ticker = Ticker
        self.mode = mode

        #вычисление даты начала стратегии в зависимости от тайфрейма
        if self.mode == 'min':
            self.from_date = datetime.now() - timedelta(2)

        elif self.mode == '5min':
            self.from_date = datetime.now() - timedelta(5)

        elif self.mode == '10min':
            self.from_date = datetime.now() - timedelta(8)

        elif self.mode == '15min':
            self.from_date = datetime.now() - timedelta(11)

        elif self.mode == '30min':
            self.from_date = datetime.now() - timedelta(19)

        elif self.mode == 'hour':
            self.from_date = datetime.now() - timedelta(41)

        elif self.mode == 'daily':
            self.from_date = datetime.now() - timedelta(600)

        elif self.mode == 'week':
            self.from_date = datetime.now() - timedelta(1200)

        elif self.mode == 'month':
            self.from_date = datetime.now() - timedelta(1800)

        
        self.to_date = datetime(2025, 12, 4) #время окончания с запасом

        self.running = True #параметр выхода из цикла

        self.cerebro = bt.Cerebro(stdstats=False)  # Инициируем "движок" BackTrader. Стандартная статистика сделок и кривой доходности не нужна

        provider1 = dict(provider_name='finam_trade', client_id=Config.ClientIds[0], access_token=Config.AccessToken)  # Торговый счет Финам
        store = FNStore(providers=[provider1]) #хранилище финам
        broker = store.getbroker(name='finam_trade')  #брокер по работе с финам
        self.cerebro.setbroker(broker)  # Устанавливаем брокера

        fp_provider_ = FinamPy(Config.AccessToken) 

        min_lot_size = fp_provider_.get_symbol_info('TQBR', self.Ticker).lot_size  #вычисление минимального размера лота акции

        self.cerebro.addsizer(bt.sizers.FixedSize, stake=min_lot_size)  #добавление расчета размера позиции на вход 

        self.cerebro.addstrategy(Strategy, TELEGRAM_TOKEN = Config.TELEGRAM_TOKEN, CHAT_ID = Config.CHAT_ID, Path =  Config.FilePath, **kwargs) #добавление стратегии и параметров Trend PullBack
        
    def run(self):
        print(f'Старт потока')

        while self.running:
            #скачивание данных с финам
            try:
                data_finam = finam.to_backtrader_data(self.Ticker, self.mode, self.from_date, self.to_date, path_save=Config.FilePath)
            except Exception as e:
                self.send_message(f'Finam export erorr {e}')

            #проверка таймфрейма
            if self.mode=='daily' or self.mode=='week' or self.mode=='month':
                dtformat='%Y-%m-%d'
            else:
                dtformat='%Y-%m-%d %H:%M:%S'

            #загрузка скаченных данных в формате backtrader
            data = bt.feeds.GenericCSVData(
                dataname=f'{Config.FilePath}{self.Ticker}.csv',
                separator =';',  # Колонки разделены табуляцией
                dtformat=dtformat,  # Формат даты 
                datetime=0, tmformat='%H:%M:%S',
                fromdate=self.from_date,  # Начальная дата приема исторических данных (Входит)
                todate=self.to_date,  # Конечная дата приема исторических данных (Не входит)
                open=3, high=4, low=5, close=6, volume=7, openinterest=-1, timeframe=bt.TimeFrame.Minutes)
        

            self.cerebro.adddata(data)  #добавляем данные

            try:
                self.cerebro.run() #запускаем бэктрейдер
            except Exception as e:
                self.send_message(f'Cerebro error {e}')

            time.sleep(60) #частота получения данных и запуска церебро
            print('GO')
        print(f'Завершение работы потока')

    def stop(self):
        self.running = False

    def send_message(self, txt):

        try:
            request = requests.get(f'https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage?chat_id={Config.CHAT_ID}&text={txt}')
        except requests.exceptions.RequestException as e:
            print(f"[Telegram] Can't send the message: {e}")

#примеры вызова стратегий
#a = Cerebro_worker('GAZP', 'min', Buy_Sell)
#a = Cerebro_worker('SBER', 'hour', Trend_PullBack, Trend = 230, PullBack = 4)
#a = a.run()
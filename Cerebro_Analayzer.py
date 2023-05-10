import finam
from datetime import datetime, timedelta
import pytz
import time
from threading import Thread
import backtrader as bt
from Config import Config
import backtrader.analyzers as btanalyzers
from Strategy.Trend_PullBack_For_Analize import Trend_PullBack_Analyze
import requests

#вычисление фиксированной позиции на одинаковую сумму денег
class FixedSizeMoney(bt.Sizer):

    params = (
        ('money', 100000),
    )

    def __init__(self):
        pass

    def _getsizing(self, comminfo, cash, data, isbuy):
        position = self.broker.getposition(data)
        if not position:
            size = self.params.money / data.close[0]
        else:
            size = position.size
        #print( size )
        return size

#функция для печти результатов анализа стратегии
def printTradeAnalysis(analyzer):
    total_open_count = analyzer.total.open
    total_closed_count = analyzer.total.closed
    total_won_count = analyzer.won.total
    total_lost_count = analyzer.lost.total
    win_streak = analyzer.streak.won.longest
    lose_streak = analyzer.streak.lost.longest
    pnl_net = round(analyzer.pnl.net.total,2)
    won_avg = round(analyzer.won.pnl.average,2)
    won_total = round(analyzer.won.pnl.total, 2)
    lost_avg = round(analyzer.lost.pnl.average,2)
    lost_total = round(analyzer.lost.pnl.total,2)
    long_total = round(analyzer.long.pnl.total,2)
    long_avg = round(analyzer.long.pnl.average,2)
    short_total = round(analyzer.short.pnl.total,2)
    short_avg = round(analyzer.short.pnl.average,2)
    lost_max = round(analyzer.lost.pnl.max,2)
    len_lost = round(analyzer.len.lost.max, 2) 
    strike_rate = round((total_won_count / total_closed_count) * 100,2)
    profit_factor = round((won_total / (-lost_total)), 2)
    
    h1 = ['Total Open', 'Total Closed', 'Total Won', 'Total Lost', 'Won avg', 'Lost avg', 'Long total', 'Long avg', 'Lost max']
    h2 = ['Strike Rate','Win Streak', 'Losing Streak', 'PnL Net', 'Won total', 'Lost total', 'Short total', 'Short avg', 'Len lost max']
    r1 = [total_open_count, total_closed_count, total_won_count, total_lost_count, won_avg, lost_avg, long_total, long_avg, lost_max]
    r2 = [strike_rate, win_streak, lose_streak, pnl_net,  won_total, lost_total, short_total, short_avg, len_lost]
    
    if len(h1) > len(h2):
        header_length = len(h1)
    else:
        header_length = len(h2)
    
    print_list = [h1,r1,h2,r2]
    row_format ="{:<12}" * (header_length + 1)
    txt = (f'Profit Factor: {profit_factor}\n'
            f'{h1[0]}: {r1[0]}\n'
            f'{h1[1]}: {r1[1]}\n'
            f'{h1[2]}: {r1[2]}\n'
            f'{h1[3]}: {r1[3]}\n'
            f'{h1[4]}: {r1[4]}\n'
            f'{h1[5]}: {r1[5]}\n'
            f'{h1[6]}: {r1[6]}\n'
            f'{h1[7]}: {r1[7]}\n'
            f'{h1[8]}: {r1[8]}\n'
            f'{h2[0]}: {r2[0]}\n'
            f'{h2[1]}: {r2[1]}\n'
            f'{h2[2]}: {r2[2]}\n'
            f'{h2[3]}: {r2[3]}\n'
            f'{h2[4]}: {r2[4]}\n'
            f'{h2[5]}: {r2[5]}\n'
            f'{h2[6]}: {r2[6]}\n'
            f'{h2[7]}: {r2[7]}\n'
            f'{h2[8]}: {r2[8]}\n'
    )

    return txt


#поток для запуска бэктрейдера
class Cerebro_Analayzer_worker(Thread):
    
    def __init__(self, Ticker, mode, from_date, to_date, Trend, PullBack):
        super().__init__()
        self.Ticker = Ticker #тикер
        self.mode = mode #торговый таймфрейм
        self.from_date = datetime.strptime(from_date, '%Y-%m-%d') #дата начала анализа стратегии
        self.to_date = datetime.strptime(to_date, '%Y-%m-%d') #дата конца анализа стратегии


        self.Trend = int(Trend) #параметр тренда стратегии
        self.Pullback = int(PullBack) #параметр отката стратегии

        
    def run(self):
        print(f'Старт потока')

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
                todate=self.to_date,  # Конечная дата приема исторических данных (Не входит) 2 26
                open=3, high=4, low=5, close=6, volume=7, openinterest=-1, timeframe=bt.TimeFrame.Minutes)
        
        
        cerebro = bt.Cerebro(optreturn=False)  # Инициируем "движок" BackTrader. Стандартная статистика сделок и кривой доходности не нужна

        cerebro.broker.setcommission(commission=0.000069) #размер комиссии

        cerebro.broker.setcash(1000000)  #стартовый капитал для "бумажной" торговли

        
        cerebro.addsizer(FixedSizeMoney, money = 100000) #добавление расчета размера позиции на вход
        #self.cerebro.addsizer(bt.sizers.PercentSizer, percents = 99) 
        #self.cerebro.addsizer(bt.sizers.FixedSize, stake = 1)

        
        cerebro.addstrategy(Trend_PullBack_Analyze, Trend = self.Trend, PullBack = self.Pullback) #добавление стратегии и параметров

        cerebro.adddata(data)  #добавляем скаченные данные
    
        #добавляем анализаторы стратегии
        cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe_ratio',  riskfreerate=0.0) 
        cerebro.addanalyzer(btanalyzers.AnnualReturn)       
        cerebro.addanalyzer(btanalyzers.Returns)                
        cerebro.addanalyzer(btanalyzers.DrawDown, _name='draw_down')              
        cerebro.addanalyzer(btanalyzers.SQN, _name='SQN')
        cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='TrAn')


        
        results = cerebro.run()  # Запуск торговой системы
        strat = results[0]

        TradeAnalysis = printTradeAnalysis(strat.analyzers.TrAn.get_analysis())

        sharpe = strat.analyzers.sharpe_ratio.get_analysis()
        if sharpe['sharperatio'] == None:
            ext_1 = None
        else:
            ext_1 = round(sharpe['sharperatio'], 2)
        drawdown = strat.analyzers.draw_down.get_analysis()
        ext_2 = round(drawdown['max']['drawdown'],2)
        ext_3 = drawdown['max']['len']
        SQN = strat.analyzers.SQN.get_analysis()
        ext_4 = round(SQN['sqn'],2)

        TradeAnalysis_2 = (#f'Sharpe =  {ext_1} \n' 
                            #f'drawdown max = {ext_2} \n'
                            #f'drawdown len max = {ext_3} \n'
                            f'SQN = {ext_4} \n' )

        self.send_message(txt = f'{self.from_date.date()} - {self.to_date.date()} \n' + TradeAnalysis_2 + TradeAnalysis)



    def send_message(self, txt):

        try:
            request = requests.get(f'https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage?chat_id={Config.CHAT_ID}&text={txt}')
        except requests.exceptions.RequestException as e:
            print(f"[Telegram] Can't send the message: {e}")



#a = Cerebro_Analayzer_worker(Ticker, mode, from_date, to_date, Trend, PullBack)
#a = Cerebro_Analayzer_worker('SBER', '30min', '2022-01-01', '2023-02-01', 230, 4)
#a = Cerebro_Analayzer_worker('SPFB.SBRF', '30min', '2022-01-01', '2023-02-01', 230, 4)
#a = Cerebro_Analayzer_worker('SPFB.SBRF', 'daily', '2020-01-01', '2023-02-01', 230, 4)
#a = a.run()
#a.start()
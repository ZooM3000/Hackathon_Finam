from telegram.ext import Updater, CommandHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import MessageHandler, Filters, InlineQueryHandler
from threading import Thread
from datetime import datetime, time
import logging
import finam
from Config import Config
from Strategy.Buy_Sell import Buy_Sell
from Strategy.Trend_PullBack import Trend_PullBack
from FinamPy import FinamPy
from Cerebro import Cerebro_worker
from Cerebro_Analayzer import Cerebro_Analayzer_worker

#инициализаци логера для записи всех действий бота
log = logging.getLogger('log')
log.setLevel(logging.DEBUG)
handler = logging.FileHandler(f'{Config.FilePath}log.log')
format = logging.Formatter('%(asctime)s  %(name)s %(levelname)s: %(message)s')
handler.setFormatter(format)
log.addHandler(handler)

print("Starting...")
log.debug('Starting...')

updater = Updater(token = Config.TELEGRAM_TOKEN)
dispatcher = updater.dispatcher

client_id = Config.ClientIds[0]
fp_provider = FinamPy(Config.AccessToken)  # Подключаемся к торговому счету


def analyze(update, context):
    """функция обработки команды '/analyze'
    запускает поток анализа стратегии"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        print("/analyze")
        log.debug('command /analyze')


        if context.args:
            if len(context.args) == 6:
                Ticker = context.args[0] #передача названия тикера в стратегию
                TimeFrame = context.args[1] #передача таймфрейма в стратегию
                from_date = context.args[2] #передача даты начала анализа стратегии
                to_date = context.args[3] #передача даты конца анализа стратегии
                Trend = context.args[4] #передача параметра Trend в стратегию
                PullBack = context.args[5] #передача параметра PullBack в стратегию

                #запуск анализа стратегии 
                str_analyze = Cerebro_Analayzer_worker(Ticker, TimeFrame, from_date, to_date, Trend, PullBack)
                str_analyze.start()

            else:
                context.bot.send_message(chat_id=update.effective_chat.id, 
                                text='Not enoght elements, you need 6')
    

        else:
            context.bot.send_message(chat_id=update.effective_chat.id, 
                                 text='No command argument')


def start(update, context):
    """функция обработки команды '/start'
    запускает два потока стратегий на выбор"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        print("/start")
        log.debug('command /start')
        global strategy

        if context.args:
            if int(context.args[0]) == 1:

                if len(context.args) == 5:
                    Ticker = context.args[1] #передача названия тикера в стратегию
                    TimeFrame = context.args[2] #передача таймфрейма в стратегию
                    Trend = context.args[3] #передача параметра Trend в стратегию
                    PullBack = context.args[4] #передача параметра PullBack в стратегию

                    
                    strategy = Cerebro_worker(Ticker, TimeFrame, Trend_PullBack, Trend = int(Trend), PullBack = int(PullBack)) #создание экземпляра стратегии Trend_PullBack
                    strategy.start() #запуск стратегии 

                    context.bot.send_message(chat_id=update.effective_chat.id, 
                                text='Strategy Trend_PullBack is start')

                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, 
                                text='Not enoght elements, you need 5')


            if int(context.args[0]) == 2:
                if len(context.args) == 3:
                    Ticker = context.args[1] #передача названия тикера в стратегию
                    TimeFrame = context.args[2] #передача таймфрейма в стратегию

                    
                    strategy = Cerebro_worker(Ticker, TimeFrame, Buy_Sell) #создание экземпляра стратегии Buy_Sell
                    strategy.start() #запуск стратегии 

                    context.bot.send_message(chat_id=update.effective_chat.id, 
                                text='Strategy Buy/Sell is start') 

                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, 
                                text='Not enoght elements, you need 3')       

        else:
            context.bot.send_message(chat_id=update.effective_chat.id, 
                                 text='No command argument')


def stop(update, context):
    """функция обработки команды '/stop' останавливает поток стратегии
    закрывает открытые позиции, открытые ордера"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /stop')

        try:
            strategy.stop() #останавливаю работу стратегии
        except Exception as e:
            pass

        #закрываю позиции если они есть
        portfolio = fp_provider.get_portfolio(client_id)  # Получаем портфель
        for position in portfolio.positions:  # Пробегаемся по всем позициям
            txt = f'Position ({position.security_code}) {position.balance} @ {position.average_price:.2f} / {position.current_price:.2f} PnL {position.unrealized_profit:.2f}'
            min_lot_size = fp_provider.get_symbol_info('TQBR', position.security_code).lot_size
            quantity = position.balance / min_lot_size
            order = fp_provider.new_order(client_id = client_id, security_board = "TQBR", 
                security_code = position.security_code, buy_sell= 'BUY_SELL_BUY' if position.balance < 0  else 'BUY_SELL_SELL', 
                quantity= int(quantity))

            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Close position {position.security_code}, transaction_id: {order.transaction_id}, PnL: {position.unrealized_profit:.2f}') #


        #закрываю стоп заявки если они есть
        stop_orders = fp_provider.get_stops(client_id).stops  # Получаем стоп заявки
        for stop_order in stop_orders:  # Пробегаемся по всем стоп заявкам
            cancel_order = fp_provider.cancel_stop(client_id, stop_order.stop_id)

            #if cancel_order != None:
            #    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Stop order: {stop_order.stop_id} canceled')
    

        context.bot.send_message(chat_id=update.effective_chat.id, 
                                 text='Strategy is stopped, positions closed, orders canceled')      


def check(update, context):
    """функция обработки команды '/check проверяет отклик севера телеграмма"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /check')
        
        context.bot.send_message(chat_id=update.effective_chat.id, 
                                 text='telegram ok')
  

def balance(update, context):
    """функция обработки команды '/balance показывает баланс счета"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /balance')

        portfolio = fp_provider.get_portfolio(client_id)  # Получаем портфель
        
        context.bot.send_message(chat_id=update.effective_chat.id, 
                                text = f'Balance {portfolio.currencies[0].balance:.2f} {portfolio.currencies[0].name}')


def position(update, context):
    """функция обработки команды /position показывает открытые позиции """
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /position')

        portfolio = fp_provider.get_portfolio(client_id)  # Получаем портфель
        for position in portfolio.positions:  # Пробегаемся по всем позициям
            txt = f'Position ({position.security_code}) {position.balance} @ {position.average_price:.2f} / {position.current_price:.2f} PnL {position.unrealized_profit:.2f}'
        if portfolio.positions==[]:
            txt = 'No positions'

        context.bot.send_message(chat_id=update.effective_chat.id, 
                                text= txt)


def orders(update, context):
    """функция обработки команды /orders показывает открытые ордера"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /orders')

        stop_orders = fp_provider.get_stops(client_id).stops  # Получаем стоп заявки
        for stop_order in stop_orders:  # Пробегаемся по всем стоп заявкам
            txt = f'  Stop order {"Buy" if stop_order.buy_sell == "Buy" else "Sell"} {stop_order.security_board}.{stop_order.security_code} {stop_order.stop_loss.quantity.value} @ {stop_order.stop_loss.activation_price}'
        if stop_orders==[]:
            txt = 'No orders'

        context.bot.send_message(chat_id=update.effective_chat.id, 
                                text=txt)


def send_log(update, context):
    """функция обработки команды /send_log отправляет log отработки"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /send_log')

        file=f'{Config.FilePath}log.log'
        
        context.bot.sendDocument(chat_id=update.effective_chat.id, document=open(file, 'r'))
         

def help(update, context):
    """функция обработки команды /help показывает перчень используемых команд"""
    if str(update.message.from_user.username) == Config.ADMIN_USER_NAME:
        log.debug('command /help')
 
        text = """
/start - Запуск стратегии (1-Trend_PullBack, 2-Buy_Sell)
/start 1 Ticker TimeFrame Trend PullBack 
/start 2 Ticker TimeFrame

/analyze - Анализ стратегии Trend_PullBack
/analyze Ticker TimeFrame from_date to_date Trend PullBack

/stop - Остановить алгоритм, закрыть все позиции, ордера 

/check - Проверка отклика Telegram бота 

/balance - Баланс счета

/position -  Отображает список позиций на бирже

/orders - Отображает список стоп ордеров на бирже

/help - Помощь по коммандам

/send_log- Отправка лога в чат (для отладки)
"""     
        context.bot.send_message(chat_id=update.effective_chat.id, 
                                text=text)

# обработчик команды '/start'
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# обработчик команды '/analyze'
analyze_handler = CommandHandler('analyze', analyze)
dispatcher.add_handler(analyze_handler)

# обработчик команды '/stop'
stop_handler = CommandHandler('stop', stop)
dispatcher.add_handler(stop_handler)

# обработчик команды '/check'
check_handler = CommandHandler('check', check)
dispatcher.add_handler(check_handler)

# обработчик команды '/balance'
balance_handler = CommandHandler('balance', balance)
dispatcher.add_handler(balance_handler)

# обработчик команды '/position'
position_handler = CommandHandler('position', position)
dispatcher.add_handler(position_handler)

# обработчик команды '/orders'
orders_handler = CommandHandler('orders', orders)
dispatcher.add_handler(orders_handler)

# обработчик команды '/help'
help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

# обработчик команды '/log'
log_handler = CommandHandler('send_log', send_log)
dispatcher.add_handler(log_handler) 


def main():
    print('main')
    log.debug('def main')
    # запуск прослушивания сообщений
    updater.start_polling()
    # обработчик нажатия Ctrl+C
    updater.idle()


if __name__ == '__main__':
    while True:

        try:
            main()
        except Exception as e:
            print('Error telegram!')
            log.debug('Error telegram!', exc_info=True)



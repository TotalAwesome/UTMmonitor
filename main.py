#####################################
#
#   28.07.2-21
#   - Changed for UTMv4
#   - Some fixes
#
#####################################

import requests
import re
import datetime
import threading
import telebot
import logging
from config import *
from time import sleep
from requests.adapters import HTTPAdapter

# Если столько раз подряд хост лежит, считаем его упавшим
S = 2 
# Время в секундах между попытками проверить узлы
sleep_time = 2
#  За сколько дней предупреждать об истечении ключей
expire = 20

class utm:

    def __init__(self,name,url):

        self.url = url
        self.name = name
        self.offlinecounter = 0
        self.version = ''
        self.license = ''
        self.checks = ''
        self.rsa = ''
        self.gost = ''
        self.state = True
        self.last_state = True
        self.notif_date = datetime.date.today()-datetime.timedelta(days=1)

    def update(self):

        p = parse_utm(self.url, self.name)
        self.version = p['версия']
        self.license = p['лицензия']
        self.checks = p['чеки']
        self.rsa = p['рса']
        self.gost = p['гост']
        self.state = p['доступ']

    def report(self):
        res = []
        res.append(self.name)
        res.append(self.version)
        res.append(self.license)
        res.append(self.checks)
        res.append(self.rsa)
        res.append(self.gost)
        res.append(self.state)
        res.append(self.last_state)
        res.append(self.offlinecounter)
        return res

def log(msg):
    print(
        f'{datetime.datetime.today()}: {msg}'
    )

def load_url(url):
    try:
        return requests.get(url+'/api/info/list')
    except Exception as e:
        log(f'Не удалось получить ответ, ошибка: {e}')
    return  None

bot = telebot.TeleBot(token, threaded = True, num_threads = 5)

def telegram():
    telebot.logger.setLevel(logging.CRITICAL)
    while True:
        try:
            bot.polling()
        except Exception as e:
            print(e)
            pass

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    msg = ''
    if 'utm_status' in message.text.lower():
        log('Отправляем информацию по всем узлам')
        t = worklist
        for i in t:
            if t[i].state == False :
                state = '🟥 '
            else:
                state = '🟩 '
            string = '{}*{}*\n*РСА*: {}\n*ГОСТ*: {}\n{}\n'
            msg = msg + string.format(  
                state,
                t[i].name,
                t[i].rsa,
                t[i].gost,
                '- '*8 
            )
        try:
            bot.send_message(message.chat.id, msg, parse_mode='Markdown' )
        except:
            log(':(')




def parse_utm(url,name):
    result = {  'версия':'',
                'лицензия':'',
                'чеки':'',
                'рса':'',
                'гост':'',
                'доступ':False}

    utm_url = url
    log(f'Парсинг {name} ({url})')
    try:
        r = load_url(utm_url).json()
        
        result['версия'] = r.get('version')
        result['лицензия'] = r.get('license')
        result['чеки'] = 'пока без чеков :)'
        tmp = r.get('rsa')
        result['рса'] = tmp.get('expireDate')
        tmp = r.get('gost')
        result['гост'] = tmp.get('expireDate')
        result['доступ'] = True

        log('Успешно')
    except:
        result['доступ'] = False
        log('Не очень успешно')
    return result

def check_date(date):
    d=re.search('(\S+)\s', date).groups(1)[0]
    s = d.split('-')
    then = datetime.date(int(s[0]),int(s[1]),int(s[2]))
    today = datetime.date.today()
    return (then - today).days

def ending(n):
    days = ['день', 'дня', 'дней']

    if n % 10 == 1 and n % 100 != 11:
        p = 0
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        p = 1
    else:
        p = 2

    return str(n) + ' ' + days[p]

def main():
    for name in utm_list:
        worklist[name] = utm(name, utm_list[name])

    while True:
        message = []
        # 🟢🔴🟠
        for utm_item in worklist:
            msg = ''
            worklist[utm_item].update()
            p = worklist[utm_item]
            if p.rsa != '' and p.gost != '' and p.notif_date != datetime.date.today() :
                rsa = check_date(p.rsa)
                gost = check_date(p.gost)
                p.notif_date = datetime.date.today()
                if rsa <= 0 :
                    message.append('🔴 *{}*\n _РСА закончился_\n'.format(p.name))
                elif rsa <= expire :
                    message.append('🟡 *{}*\n  _РСА заканчивается ({})_\n'.format(p.name,ending(rsa)))

                if gost <= 0 :
                    message.append('🔴 *{}*\n _ГОСТ закончился_'.format(p.name))
                elif gost <= expire :
                    message.append('🟡 *{}*\n _ГОСТ заканчивается ({})_\n'.format(p.name,ending(gost)))

            if p.state == False and p.offlinecounter == S:
                message.append('❌ *{}*'.format(p.name))
            elif p.state == True and p.offlinecounter >= S:
                message.append('✅ *{}*'.format(p.name))

            if p.state == True   :
                worklist[utm_item].offlinecounter = 0
            else:
                worklist[utm_item].offlinecounter = worklist[utm_item].offlinecounter + 1

        if len(message) > 0:
            for line in message:
                msg = msg + line+'\n'

        if len(msg) > 0 :
            try :
                bot.send_message( chat_id ,msg , parse_mode='Markdown')
                log('Отправка сообщения с изменениями')
            except:
                log('Неудачная отправка')
        sleep(sleep_time)

worklist = {}
tele_thread = threading.Thread(target = telegram)
tele_thread.start()

print('main')
main()





import requests
import re
import datetime
import threading
import telebot
import logging
from config import *
from time import sleep
from requests.adapters import HTTPAdapter



S = 2 # Если столько раз подряд хост лежит, считаем его упавшим
sleep_time = 2
expire = 20


def log(msg):
    s = str(datetime.datetime.today())+': '+str(msg)
    print(s)

def load_url(url):
    try:
        s = requests.Session()
        s.mount('http://',HTTPAdapter(max_retries=3))
        return s.get(url)
    except :
        pass
    return  None


bot = telebot.TeleBot(token, threaded = True, num_threads = 5)

def telegram():

    # logger = telebot.logger
    telebot.logger.setLevel(logging.CRITICAL)

    while True:
        try:
            bot._TeleBot__non_threaded_polling(none_stop = False)
        except Exception as e:
            print (e)
            pass

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    msg = ''
    if 'utm_status' in message.text.lower():
        t = worklist
        for i in t:
            string = '*{}* {} \n *RSA* : {}, *GOST* : {}'
            if t[i].state == False :
                state = '❌ недоступен'
            else:
                state = '✅ доступен'
            msg = msg + string.format(  t[i].name,
                                        state,
                                        t[i].rsa,
                                        t[i].gost ) + '\n\n'
        try:
            bot.send_message(message.chat.id, msg, parse_mode='Markdown' )
        except:
            log(':(')
        del(t)



class Utm:

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

        p = parse_utm(self.url,self.name)
        if p['версия'] !=''     : self.version = p['версия']
        if p['лицензия'] != ''  : self.license = p['лицензия']
        if p['чеки'] != ''      : self.checks = p['чеки']
        if p['рса'] != ''       : self.rsa = p['рса']
        if p['гост'] != ''      : self.gost = p['гост']
        if p['доступ'] !=''     : self.state = p['доступ']
        #if self.state == False  : self.offlinecounter = self.offlinecounter+1

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

def parse_utm(url,name):
    result = {  'версия':'',
                'лицензия':'',
                'чеки':'',
                'рса':'',
                'гост':'',
                'доступ':False}

    utm_url = url
    log(f'Парсим утм {name} ({url})')
    try:
        r = load_url(utm_url)
        res = re.search(r'.*ПО.*">(\d.\d+\.\d+)',r.text)
        if res is not None:
            result['версия'] = res.group(1)
        else:
            result['версия'] = 'ошибка парсинга'

        res = re.search(r'деятельности (.*)</div></div>',r.text)
        if res is not None:
            result['лицензия'] = res.group(1)
        else:
            result['лицензия'] = 'ошибка парсинга'

        res = re.search(r'чеки.*">(.*)</div></div>',r.text)
        if res is not None:
            result['чеки'] = res.group(1)
        else:
            result['чеки'] = 'ошибка парсинга'

        res = re.search(r'RSA.* по ([-0-9]+)\s',r.text)
        if res is not None:
            result['рса'] = res.group(1)
        else:
            result['рса'] = 'ошибка парсинга'

        res = re.search(r'ГОСТ.* по ([-0-9]+)\s',r.text)
        if res is not None:
            result['гост'] = res.group(1)
        else:
            result['гост'] = 'ошибка парсинга'

        result['доступ'] = True
        # return result
        del(r)
        del(res)
        log('Успешно')
    except:
        result['доступ'] = False
        log('Не очень успешно')
    return result

def check_date(date):
    s = date.split('-')
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
        worklist[name] = Utm (name, utm_list[name])

    while True:
        message = []

        for utm_item in worklist:
            msg = ''
            worklist[utm_item].update()
            p = worklist[utm_item]
            if p.rsa != '' and p.gost != '' and p.notif_date != datetime.date.today() :
                rsa = check_date(p.rsa)
                gost = check_date(p.gost)
                p.notif_date = datetime.date.today()
                if rsa <= 0 :
                    message.append('.. РСА на *{}* закончился'.format(p.name))
                elif rsa <= expire :
                    message.append('❗️ РСА на *{}* заканчивается через {}'.format(p.name,ending(rsa)))

                if gost <= 0 :
                    message.append('.. ГОСТ на *{}* закончился'.format(p.name))
                elif gost <= expire :
                    message.append('❗ГОСТ на *{}* заканчивается через {}'.format(p.name,ending(gost)))

            if p.state == False and p.offlinecounter == S:
                message.append('❌ *{}* Недоступен'.format(p.name))
            elif p.state == True and p.offlinecounter >= S:
                message.append('✅ *{}* Доступен'.format(p.name))

            if p.state == True   :
                worklist[utm_item].offlinecounter = 0
            else:
                worklist[utm_item].offlinecounter = worklist[utm_item].offlinecounter + 1
            del(utm_item)

        if len(message) > 0:
            for line in message:
                msg = msg + line+'\n'

        if len(msg) > 0 :
            log(str(datetime.datetime.today())+ ' Send message to telegram')
            try :
                bot.send_message( chat_id ,msg , parse_mode='Markdown')
                log('Отправка сообщения')
            except:
                log('Отправка не удалась')
        del(msg)
        sleep(sleep_time)

global worklist
worklist = {}
tele_thread = threading.Thread(target = telegram)
tele_thread.start()

print('main')
main()





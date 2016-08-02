import argparse
import logging
import smtplib
import evelink
from evelink.api import APIError
from apscheduler.schedulers.blocking import BlockingScheduler

import credentials
from key_manager import KeyManager
from notificationIDmap import id_map

key_store = 'keys.json'
iteration = dict()  # checks every hour, every 24 hours a 'i'm still here' mail will be send, this is the 24 counter


def add_char():
    new_key = input('API key: ')
    new_vcode = input('Verification Code: ')
    api = evelink.api.API(api_key=(new_key, new_vcode))
    acc = evelink.account.Account(api)
    try:
        chars = acc.characters()
        number = 0
        num2char = {}
        for charID in chars.result:
            char = chars.result[charID]
            print('{id}) {name} ({corp})'.format(id=number, name=char['name'], corp=char['corp']['name']))
            num2char[number] = charID
            number += 1
        try:
            charNumber = int(input('Select a Character: '))
            email = input('Associated email address: ')
            name = chars.result[num2char[charNumber]]['name']
            km = KeyManager(key_store)
            km.add(new_key, new_vcode, num2char[charNumber], name, email)
            print('Added character {name} successfully'.format(name=name))
        except ValueError:
            print('wrong input')
            exit(2)
    except APIError:
        exit(1)
        print('Authentication failure.')
    exit(0)


def list_char():
    km = KeyManager(key_store)
    num = 0
    for key in km.keys:
        print('{num}) {name}, API key: {apiK}, email: {email}'.format(num=num, name=key[3], apiK=key[0], email=key[4]))
        num += 1


def rm_char():
    list_char()
    try:
        rm = int(input('which character should be deleted: '))
        km = KeyManager(key_store)
        km.remove(rm)
    except (ValueError, IndexError):
        print('wrong input')
        exit(2)


def do_stuff():
    global iteration
    km = KeyManager(key_store)
    logging.info('starting scan')
    s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    s.ehlo()
    s.login(credentials.email, credentials.emailPW)
    logging.info('connected to mail server')
    for key in km.keys:
        kit = iteration[key]
        api = evelink.api.API(api_key=(key[0], key[1]))
        char = evelink.char.Char(char_id=key[2], api=api)
        res = char.notifications()

        rec_name = key[3]
        receiver = key[4]

        if len(res.result) == 0:
            kit += 1
            if kit == 24:
                subject = 'No new notifications for {name}'.format(name=rec_name)
                text = 'No new notifications within the last 24 hours for character {name}.'.format(name=rec_name)
                logging.info('24 hour check in for char {char}'.format(char=rec_name))
            else:
                logging.info('nothing new for {char}'.format(char=rec_name))
                iteration[key] = kit
                return
        else:
            logging.info('{nonn} new notification(s) for {name}'.format(name=rec_name, nonn=len(res.result)))
            subject = '{nonn} new notification(s) for {name}'.format(name=rec_name, nonn=len(res.result))
            lines = []
            for r in res.result:
                if r['read'] == 1:
                    continue  # was already read in client
                lines.append('{date}: {type} from {sender}'.format(date=r['sentDate'], type=id_map[r['typeID']],
                                                                   sender=r['senderName']))
            text = 'Character {name} has the following new notifications: \r\n'.format(name=rec_name)
            text += '\r\n'.join(lines)

        iteration[key] = 0  # reset iteration counter
        msg = '\r\n'.join([
            'From: {email}'.format(email=credentials.email),
            'To: {recv}'.format(recv=receiver),
            'Subject: {sub}'.format(sub=subject),
            '',
            '{text}'.format(text=text)
        ])
        sent = s.sendmail(credentials.email, [receiver], msg)
        if len(sent) == 0:
            logging.info(
                'successfully sent mail to {recv}: {subj} - {text}'.format(recv=receiver, subj=subject, text=text))
        else:
            logging.warning('error with receiver {recv}: {error}'.format(recv=receiver, error=str(sent)))
    s.close()
    logging.info('scan done, mail server connection closed')


if __name__ == '__main__':
    cmds = ['add', 'list', 'remove', 'start']
    parser = argparse.ArgumentParser('an eve api scanner and mailer daemon')
    parser.add_argument('action', help='command: {cmds}'.format(cmds=', '.join(cmds)), choices=cmds)
    parser.add_argument('-ks', '--key_store', help='where to store the api keys', default=key_store)
    args = parser.parse_args()

    global key_store
    key_store = args.key_store

    logging.basicConfig(format='%(asctime)s %(message)s', filename='log.log', filemode='w', level=logging.INFO)

    if args.action == 'add':
        add_char()

    elif args.action == 'list':
        list_char()

    elif args.action == 'remove':
        rm_char()

    elif args.action == 'start':
        km = KeyManager(key_store)
        if len(km.keys) == 0:
            print('no keys, add one with the add command')
            exit(3)
        for k in KeyManager(key_store).keys:
            iteration[k] = 0  # init 24 hour counter for every key
        scheduler = BlockingScheduler()
        scheduler.add_job(do_stuff, 'interval', hours=1)
        try:
            print('starting scheduler...')
            logging.info('starting scheduler...')
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=False)
            print('scheduler stopped')
            logging.warning('scheduler stopped')
    else:
        print('unknown action {act}'.format(act=args.action))

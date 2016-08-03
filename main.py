import argparse
import logging
import smtplib
from datetime import datetime

import evelink
from evelink.api import APIError
from pytz import utc
from apscheduler.schedulers.blocking import BlockingScheduler

import credentials
from key_manager import KeyManager
from notificationIDmap import id_map
from storage_dict import StorageDictList

key_store_path = ''
notify_store_path = ''
iteration = dict()  # checks every hour, every 24 hours a 'i'm still here' mail will be send, this is the 24 counter
notify_store = dict()  # maps notification IDs to a char name to prevent sending mails about the same notification


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
            km = KeyManager(key_store_path)
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
    km = KeyManager(key_store_path)
    num = 0
    if len(km.keys) == 0:
        print('no keys, add one with the add command')
        exit(3)
    for key in km.keys:
        print('{num}) {name}, API key: {apiK}, email: {email}'.format(num=num, name=key[3], apiK=key[0], email=key[4]))
        num += 1


def rm_char():
    list_char()
    try:
        rm = int(input('which character should be deleted: '))
        km = KeyManager(key_store_path)
        km.remove(rm)
    except (ValueError, IndexError):
        print('wrong input')
        exit(2)


def test_mail():
    target = input('target mail address for test: ')
    s = smtplib.SMTP_SSL(credentials.smtp_server, credentials.smtp_port)
    s.ehlo()
    s.login(credentials.email_user, credentials.email_password)
    print('logged in at mail server')
    msg = '\r\n'.join([
        'From: {email}'.format(email=credentials.email),
        'To: {recv}'.format(recv=target),
        'Subject: EVE Notifications Test',
        '',
        "looks like it's working"
    ])
    sent = s.sendmail(credentials.email, [target], msg)
    if len(sent) == 0:
        print('should have worked')
    else:
        print('error with address: {s}'.format(s=sent))
    s.close()


def do_stuff():
    global iteration, notify_store
    km = KeyManager(key_store_path)
    logging.info('starting scan')
    s = smtplib.SMTP_SSL(credentials.smtp_server, credentials.smtp_port)
    s.ehlo()
    s.login(credentials.email_user, credentials.email_password)
    logging.info('connected to mail server')
    for key in km.keys:
        kit = iteration[tuple(key)]
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
                logging.info('nothing new for {char} ({tries}/24)'.format(char=rec_name, tries=kit))
                iteration[tuple(key)] = kit
                continue
        else:
            lines = []
            for r in res.result:
                noti = res.result[r]
                if noti['read'] == 1:
                    notify_store.remove(rec_name, noti['id'])
                    continue  # was already read in client
                if notify_store.contains(rec_name, noti['id']):
                    continue  # was already sent once
                lines.append('{time}: {type}'.format(
                    time=datetime.utcfromtimestamp(int(noti['timestamp'])).isoformat().replace('T', ' '),
                    type=id_map[noti['type_id']]))
                notify_store.add(rec_name, noti['id'])
            if len(lines) == 0:
                continue  # every notification was either read or already sent, nothing new
            subject = '{nonn} new notification(s) for {name}'.format(name=rec_name, nonn=len(lines))
            logging.info('{subj}'.format(subj=subject))
            text = 'Character {name} has the following new notifications: \r\n'.format(name=rec_name)
            text += '\r\n'.join(lines)

        iteration[tuple(key)] = 0  # reset iteration counter
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
                'successfully sent mail to {recv}: {subj} - {text}'.format(recv=receiver, subj=subject,
                                                                           text=text.replace('\r\n', '\\r\\n')))
        else:
            logging.warning('error with receiver {recv}: {error}'.format(recv=receiver, error=str(sent)))
    s.close()
    logging.info('scan done, mail server connection closed')


if __name__ == '__main__':
    cmds = ['add', 'list', 'remove', 'start', 'test']
    parser = argparse.ArgumentParser('an eve api scanner and mailer daemon')
    parser.add_argument('action', help='command: {cmds}'.format(cmds=', '.join(cmds)), choices=cmds)
    parser.add_argument('-ks', '--key_store', help='where to store the api keys', default='keys.json')
    parser.add_argument('-l', '--log', help='log file location', default='log.log')
    parser.add_argument('-ns', '--notify_store', help='where to store already sent notifies', default='notifies.json')
    args = parser.parse_args()

    key_store_path = args.key_store
    notify_store_path = args.notify_store

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', filename=args.log, filemode='w',
                        level=logging.INFO)

    if args.action == 'add':
        add_char()

    elif args.action == 'list':
        list_char()

    elif args.action == 'remove':
        rm_char()

    elif args.action == 'start':
        km = KeyManager(key_store_path)
        if len(km.keys) == 0:
            print('no keys, add one with the add command')
            exit(3)
        for k in KeyManager(key_store_path).keys:
            iteration[tuple(k)] = 0  # init 24 hour counter for every key

        notify_store = StorageDictList(notify_store_path)
        scheduler = BlockingScheduler(timezone=utc)
        scheduler.add_job(do_stuff, 'interval', hours=1)
        try:
            print('starting scheduler...')
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=False)
            print('scheduler stopped')
    elif args.action == 'test':
        test_mail()
    else:
        print('unknown action {act}'.format(act=args.action))

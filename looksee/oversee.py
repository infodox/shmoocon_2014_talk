import logging
import socket
import re

from multiprocessing import Process
from functools import wraps

from redislog.logger import RedisLogger
from redislog.handlers import RedisHandler

from tasa.store import connection

import looksee_logging
import looksee_conf  # This could probably be more smooth

log = logging.getLogger('oversee')


def ignore_keyboardinterrupt(f):
    """ Don't produce a traceback on ctrl-c """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args ,**kwargs)
        except KeyboardInterrupt:
            pass
    return wrapper


message_lookup = {
    'restart': lambda: exit(1),
    'stop': lambda: exit(0),
    }


@ignore_keyboardinterrupt
def listen_for_halt():
    pubsub = connection.pubsub()
    pubsub.subscribe('control')
    for message in pubsub.listen():
        if message['type'] == 'message':
            message_lookup[message['data']]()


if __name__ == '__main__':
    log.info("Starting listener...")
    listen_proc = Process(target=listen_for_halt, args=())
    listen_proc.start()

    processes = []

    fqdn = socket.getfqdn()
    for w in looksee_conf.workers:
        if re.match(w['host'], fqdn):
            for x in range(w['count']):
                proc = Process(target=w['func'], args=())
                proc.start()
                processes.append(proc)
    try:
        listen_proc.join()
    except KeyboardInterrupt:
        pass
    for proc in processes:
        proc.terminate()
    log.info("Exiting...")

import praw
import time
import schedule
import configparser
import pickledb
from requests import get
from requests.exceptions import ConnectionError


def wait_until_online(timeout, slumber):
    offline = 1
    t = 0
    while offline:
        try:
            r = get('https://google.com', timeout=timeout).status_code
        except ConnectionError:
            r = None
        if r == 200:
            offline = 0
        else:
            t += 1
            if t > 3:
                quit()
            else:
                print('BOT OFFLINE')
                time.sleep(slumber)


def do_db(db, id, sub, test_mode):
    if not db.exists(id):
        db.set(id, sub)
        if not test_mode:
            db.dump()
        return True


def sniper(reddit, read_subreddits, write_subreddits, send_replies, crosspost, test_mode, db):
    wait_until_online(10, 3)
    last_day_epoch = int(time.time()) - 86400

    for read_subreddit in read_subreddits:
        for submission in reddit.subreddit(read_subreddit).new(limit=None):
            if not submission.stickied and submission.created_utc >= last_day_epoch:
                title = submission.title
                selftext = submission.selftext
                if do_db(db, submission.id, read_subreddit, test_mode):
                    for write_subreddit in write_subreddits:
                        if crosspost:
                            if not test_mode:
                                submission.crosspost(subreddit=write_subreddit, send_replies=send_replies)
                        else:
                            if not test_mode:
                                reddit.subreddit(write_subreddit).submit(title, selftext=selftext, send_replies=send_replies)

                        print(f'r/{read_subreddit} → r/{write_subreddit} - {title[0:80]}')
                        time.sleep(900)
                    break


def main():
    db = pickledb.load('history.db', False)
    config = configparser.ConfigParser()
    config.read('conf.ini')
    read_subreddits = [x.strip() for x in config['SETTINGS']['read_subreddits'].split(',')]
    write_subreddits = [x.strip() for x in config['SETTINGS']['write_subreddits'].split(',')]
    send_replies = config['SETTINGS'].getboolean('send_replies')
    crosspost = config['SETTINGS'].getboolean('crosspost')
    min_sleep = int(config['SETTINGS']['min_sleep'])
    max_sleep = int(config['SETTINGS']['max_sleep'])
    test_mode = config['SETTINGS'].getboolean('test_mode')
    reddit = praw.Reddit(
        username=config['REDDIT']['reddit_user'],
        password=config['REDDIT']['reddit_pass'],
        client_id=config['REDDIT']['reddit_client_id'],
        client_secret=config['REDDIT']['reddit_client_secret'],
        user_agent='Crossposter (by u/impshum)'
    )

    if test_mode:
        print('\nTEST MODE\n')

    sniper(reddit, read_subreddits, write_subreddits,
           send_replies, crosspost, test_mode, db)

    schedule.every(min_sleep).to(max_sleep).seconds.do(sniper, reddit=reddit, read_subreddits=read_subreddits, write_subreddits=write_subreddits, send_replies=send_replies, crosspost=crosspost, test_mode=test_mode, db=db)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()

import collections
import hashlib
import json
import os
import sys

import feedparser
import mastodon
import jinja2

from apscheduler.schedulers.blocking import BlockingScheduler


Config = collections.namedtuple('Config', ['host', 'token', 'feed_url', 'msg_format'])


def savefile_name(config):
    key = f'{config.host}:{config.token}:{config.feed_url}'
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def savefile_path(name: str) -> str:
    return os.path.join('saved', name)


def post_feed(config: Config):
    savefile = savefile_path(savefile_name(config))

    try:
        with open(savefile) as f:
            processed = json.loads(f.read())
    except Exception:
        processed = []

    client = mastodon.Mastodon(
        api_base_url=config.host,
        access_token=config.token,
    )

    feed = feedparser.parse(config.feed_url)
    template = jinja2.Template(config.msg_format)

    for entry in reversed(feed.entries):
        if entry.id in processed:
            continue

        try:
            print(f'Post: {entry.title}')
            msg = template.render(**entry)
            client.status_post(status=msg, language='ko')
        except Exception as e:
            print(e)
        else:
            processed.append(entry.id)

    processed = processed[-len(feed.entries):]

    with open(savefile, 'w') as f:
        f.write(json.dumps(processed))


def main():
    configs: list[Config] = []
    num = 0

    default_host = os.environ.get('HOST')
    default_format = os.environ.get('FORMAT', '{{title}}\n{{summary}}\n\n{{link}}')

    while True:
        try:
            host = os.environ.get(f'HOST{num}', default_host)
            token = os.environ[f'TOKEN{num}']
            feed_url = os.environ[f'FEED_URL{num}']
            msg_format = os.environ.get(f'FORMAT{num}', default_format)
        except KeyError:
            break
        configs.append(Config(host, token, feed_url, msg_format))
        num += 1

    if not configs:
        print('No config is specified.')
        return 1

    print(f'There are {len(configs)} configs.')

    for i, config in enumerate(configs):
        client = mastodon.Mastodon(
            api_base_url=config.host,
            access_token=config.token,
        )
        me = client.me()
        print(f'Account {i}: {me["acct"]}')

    scheduler = BlockingScheduler()
    for config in configs:
        scheduler.add_job(
            post_feed,
            'interval',
            args=[config],
            seconds=60,
        )

    for job in scheduler.get_jobs():
        job.func(*job.args)
    scheduler.start()


if __name__ == '__main__':
    sys.exit(main())

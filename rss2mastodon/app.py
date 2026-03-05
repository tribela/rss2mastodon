import collections
import hashlib
import html
import json
import os
import sys

import feedparser
import jinja2
import mastodon

from apscheduler.schedulers.blocking import BlockingScheduler

from rss2mastodon.sed import SedRule, apply_sed_rules, parse_sed_expressions


MAX_RECENT_ENTRIES = 200
MAX_POST_AT_ONCE = 3


Config = collections.namedtuple('Config', ['host', 'token', 'feed_url', 'msg_format', 'sed_rules'])


def savefile_name(config):
    key = f'{config.host}:{config.token}:{config.feed_url}'
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def savefile_path(name: str) -> str:
    return os.path.join('saved', name)


def post_feed(name: str, config: Config):
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

    count = 0
    for entry in reversed(feed.entries):
        if entry.id in processed:
            continue

        try:
            print(f'{name} Post: {entry.title}')
            # XXX: Note that updating entry.summary is not affecting entry['summary']
            entry['summary'] = html.unescape(entry.summary)
            msg = template.render(**entry)
            msg = apply_sed_rules(msg, config.sed_rules)
            client.status_post(status=msg, language='ko')
        except Exception as e:
            print(e)
        else:
            processed.append(entry.id)
            count += 1

        if count >= MAX_POST_AT_ONCE:
            break

    processed = processed[-MAX_RECENT_ENTRIES:]

    with open(savefile, 'w') as f:
        f.write(json.dumps(processed))


def main():
    configs: list[Config] = []
    num = 0

    default_host = os.environ.get('MASTODON_HOST')
    default_format = os.environ.get('MSG_FORMAT', '{{title}}\n{{summary}}\n\n{{link}}')
    default_sed = os.environ.get('SED', '')

    while True:
        try:
            host = os.environ.get(f'HOST{num}', default_host)
            token = os.environ[f'TOKEN{num}']
            feed_url = os.environ[f'FEED_URL{num}']
            msg_format = os.environ.get(f'FORMAT{num}', default_format)
            msg_format = msg_format.replace(r'\n', '\n')
            sed_expr = os.environ.get(f'SED{num}', default_sed)
            sed_rules: list[SedRule] = parse_sed_expressions(sed_expr) if sed_expr else []
        except KeyError:
            break
        configs.append(Config(host, token, feed_url, msg_format, sed_rules))
        num += 1

    if not configs:
        print('No config is specified.')
        return 1

    print(f'There are {len(configs)} configs.')

    scheduler = BlockingScheduler()
    for i, config in enumerate(configs):
        client = mastodon.Mastodon(
            api_base_url=config.host,
            access_token=config.token,
        )
        me = client.me()
        name = me['acct']
        print(f'Account {i}: {name}')

        scheduler.add_job(
            post_feed,
            'interval',
            args=[name, config],
            seconds=60,
        )

    for job in scheduler.get_jobs():
        job.func(*job.args)
    scheduler.start()


if __name__ == '__main__':
    sys.exit(main())

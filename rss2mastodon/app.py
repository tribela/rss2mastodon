import collections
import hashlib
import html
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

import feedparser
import jinja2
import mastodon
import schedule

from rss2mastodon.sed import apply_sed_rules, parse_sed_expressions, SedRule


MAX_RECENT_ENTRIES = 200
MAX_POST_AT_ONCE = 3
POST_TIMEOUT_S = 240
FEED_FETCH_TIMEOUT_S = 30
MASTODON_TIMEOUT_S = 120


Config = collections.namedtuple('Config', ['host', 'token', 'feed_url', 'msg_format', 'sed_rules'])


def savefile_name(config):
    key = f'{config.host}:{config.token}:{config.feed_url}'
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def savefile_path(name: str) -> str:
    return os.path.join('saved', name)


def fetch_feed(url: str, timeout: int = FEED_FETCH_TIMEOUT_S) -> bytes:
    """Download RSS feed content with explicit timeout.

    feedparser.parse() does not accept a timeout parameter and uses
    urllib with the default (infinite) socket timeout, which can cause
    the program to hang indefinitely if the RSS server stops responding.
    """
    req = urllib.request.Request(url, headers={'User-Agent': 'rss2mastodon/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


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
        request_timeout=MASTODON_TIMEOUT_S,
    )

    # Fetch feed with timeout before parsing — feedparser.parse() has no
    # timeout parameter and can hang forever on unresponsive servers.
    try:
        feed_data = fetch_feed(config.feed_url)
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        print(f'{name}: Feed fetch failed ({config.feed_url}): {e}')
        return

    feed = feedparser.parse(feed_data)
    template = jinja2.Template(config.msg_format)
    deadline = time.time() + POST_TIMEOUT_S

    count = 0
    for entry in reversed(feed.entries):
        if entry.id in processed:
            continue

        if time.time() > deadline:
            print(f'Timeout ({POST_TIMEOUT_S}s) reached for {config.feed_url}, saving progress')
            break

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

    for i, config in enumerate(configs):
        client = mastodon.Mastodon(
            api_base_url=config.host,
            access_token=config.token,
        )
        me = client.me()
        name = me['acct']
        print(f'Account {i}: {name}')

        schedule.every(5).minutes.do(post_feed, name=name, config=config)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print(f'Unhandled error in scheduled job: {e}')
            # Continue the loop — one failed job must not stop all feeds.

        idle = schedule.idle_seconds()
        time.sleep(max(idle if idle is not None else 0, 0))


if __name__ == '__main__':
    sys.exit(main())

# RSS 2 Mastodon

Post RSS feed to Mastodon bot

It supports multiple accounts

## Configuration

```env
# Default host (Optional)
MASTODON_HOST=https://default.tld

# Default message format (Optional)
MSG_FORMAT={{title}}\n{{summary}}\n\n{{link}}

HOST0=https://mastodon.tld
TOKEN0=someaccesstoken
FEED_URL0=https://rss.tld/feed.xml
FORMAT0={{title}}\n{{link}}\n#news

HOST1=https://mastodon.tld
TOKEN1=anotheraccesstoken
FEED_URL1=https://rss.tld/anotherfeed.xml
FORMAT1={{title}}\n{{link}}\n#cats

# Default sed-style replacement (Optional)
# Multiple rules separated by semicolons
# Flags: g (global), i (case-insensitive), m (multiline), s (dotall)
SED=s/foo/bar/g;s/baz/qux/

# Per-account sed override (Optional, falls back to SED)
SED0=s/hello/world/
```

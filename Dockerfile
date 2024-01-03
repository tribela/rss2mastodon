FROM python:3.10

WORKDIR /app

COPY . .
RUN pip install .

CMD ["rss2mastodon"]

FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .
RUN pip install .

CMD ["rss2mastodon"]

FROM python:3.7

RUN pip install python-telegram-bot
RUN pip install requests
RUN pip install emojis
RUN pip install bs4

RUN mkdir /app
ADD . /app
WORKDIR /app

CMD python /app/bot.py
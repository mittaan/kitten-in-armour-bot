FROM python:3.11-slim-bookworm

WORKDIR /usr

RUN apt-get update && apt-get install -y sqlite3

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN pip install tenacity==9.0.0 --ignore-installed

COPY . .

WORKDIR /usr/src/db

RUN sqlite3 database.db < database.sql

WORKDIR /usr/src
CMD ["python", "kitten-in-armour-bot.py"]
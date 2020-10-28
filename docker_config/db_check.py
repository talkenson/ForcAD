"""
db.check.py
This script will check whether the postgres container is up and running. It'll
connect to the database with the credentials provided in the environment
variables.
"""

import kombu
import os
import psycopg2
import sys


def database_check():
    dbname = os.environ['POSTGRES_DB']
    user = os.environ['POSTGRES_USER']
    password = os.environ['POSTGRES_PASSWORD']
    host = os.environ['POSTGRES_HOST']
    port = os.environ['POSTGRES_PORT']

    print(f"HOST: {host}:{port}, DB: {dbname}, USER: {user}")

    # noinspection PyBroadException
    try:
        psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port)
    except:
        sys.exit(1)


def broker_check():
    host = os.environ['RABBITMQ_HOST']
    user = os.environ['RABBITMQ_DEFAULT_USER']
    port = os.environ['RABBITMQ_PORT']
    password = os.environ['RABBITMQ_DEFAULT_PASS']
    vhost = os.environ['RABBITMQ_DEFAULT_VHOST']

    broker_url = f'amqp://{user}:{password}@{host}:{port}/{vhost}'
    c = kombu.Connection(broker_url)

    # noinspection PyBroadException
    try:
        c.connect()
    except:
        sys.exit(1)


if __name__ == "__main__":
    database_check()
    broker_check()

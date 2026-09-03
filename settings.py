import os
from dotenv import load_dotenv

load_dotenv('.env')

DB_HOST = os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DB_PORT', 5432)
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')

SQLALCHEMY_DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

DEBUG = os.getenv('DEBUG', True) == 'True'
APP_CONFIG = {'title': 'fastapi-app', 'debug': DEBUG}
if not DEBUG:
    APP_CONFIG['openapi_url'] = None

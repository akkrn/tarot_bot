#!/bin/bash

# Выполнить миграции Alembic до последней версии
alembic upgrade head

# Запустить ваше Python приложение
python bot/bot.py


#!usr/bin/python3
import datetime
import hashlib
import string
import os
import random
import requests
import re

from flask import Flask, request
import peewee as pw
import telebot

from database import KarmaUser, Limitation
from logger import main_log
from telebot import types
import config

main_log.info("Program starting")
TELEGRAM_API = os.environ["telegram_token"]
bot = telebot.TeleBot(TELEGRAM_API)

saves_database = {}
database="dss4fgfd"
saves_database_id = {}
database_id="111111"
saves_database_time = {}
database_time="3333"

def is_my_message(msg):
	"""
	Функция для проверки, какому боту отправлено сообщение.
	Для того, чтобы не реагировать на команды для других ботов.
	:param msg: Объект сообщения, для которого проводится проверка.
	"""
	text = msg.text.split()[0].split("@")
	if len(text) > 1:
		if text[1] != config.bot_name:
			return False
	return True


@bot.message_handler(commands=["start"], func=is_my_message)
def start(msg):
	"""
	Функция для ответа на сообщение-команду для приветствия пользователя.
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'start'")

	reply_text = (
			"Здравствуйте, я бот, который отвечает за " +
			" подсчет кармы в чате @khvchat.")
	bot.send_message(msg.chat.id, reply_text)


@bot.message_handler(commands=["h"], func=is_my_message)
def helps(msg):
	"""
	Функция для отправки списка общедоступных команд для бота
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'help'")

	bot.send_chat_action(msg.chat.id, "typing")

	help_mess = "<b>ХабЧат</b> - чат города Хабаровска.\
	\n\nℹ️ Выражения похвалы и общение в положительном ключе повышают карму, ругательства понижают.\
	\n\n<b>Команды:</b>\
	\n/h - Справка. \
	\n/weather - Погода. \
	\n/no - Для объявлений. \
	\n/report - Отправить жалобу.\
	\n\n<b>утра, цитата, превед, фсб, фото, войс, крокодил, !?, !v, vs, save, язаБан</b> - Ответом на сообщение.\
	\n\n<b>Карма:</b>\
	\n/my - Посмотреть свою карму.\
	\n/top - Узнать наиболее благодаримых в чате.\
	\n<b>тиндер</b> - Найти пару.\
	\n<b>🎲🎰🏀🎳⚽️</b> - Рандом кармы.\
	\n/gift - Подарить +5 карму.\
	\n/freez - Заморозка кармы.\
	\n/unfreez - Разморозка."
	
	
	bot.send_message(msg.chat.id, help_mess, parse_mode="HTML")

@bot.message_handler(commands=["weather"], func=is_my_message)
def weather(msg):
	"""
	Функция, которая по запросу возвращает ссылку на гитхаб-репозиторий,
	в котором хранится исходный код бота
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'source'")
	bot.send_chat_action(msg.chat.id, "typing")
	reply_text = "<a href=\"https://t.me/iv?url=https://khabara.ru/weather.php&rhash=c036525856601d\">погода</a>"
	bot.reply_to(msg, reply_text, parse_mode="HTML")
	
@bot.message_handler(commands=["report"], func=is_my_message)
def report(msg):
	"""
	Функция, для жалоб админам
	"""    
	report_text = "⚠️ Жалоба получена! \
	\nУведомление админов: " + config.adminschat
	bot.reply_to(msg, report_text)
	
@bot.message_handler(commands=["no"], func=is_my_message)
def nos(msg):
	"""
	Функция, для маркета
	"""
	main_log.info("Starting func 'nos'") 
	nos_text = "ℹ️ Здесь Чат общения, для объявлений воспользуйтесь группами: @market27 или @khvjob"
	user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
	if msg.reply_to_message:
		bot.reply_to(msg.reply_to_message,nos_text)
		bot.delete_message(msg.chat.id, msg.message_id)
		if user.status == 'administrator' or user.status == 'creator':
			bot.delete_message(msg.chat.id, msg.reply_to_message.message_id)
	else:
		bot.reply_to(msg,nos_text)
		bot.delete_message(msg.chat.id, msg.message_id)

	

def select_user(user, chat):
	"""
	Функция для извлечения данных о пользователе
	:param user: пользователь, данные которого необходимы
	:param chat: чат, в котором находится пользователь

	TODO Хотелось бы избавиться от этой функции
	"""
	main_log.info(f"Select user with id:{user.id} and chat:{chat.id}")

	selected_user = KarmaUser.select().where(
		(KarmaUser.userid == user.id) &
		(KarmaUser.chatid == chat.id)).get()
	return selected_user


def insert_user(user, chat):
	"""
	Функция для добавления нового пользователя
	:param user: данные добавляемого пользователя
	:param chat: чат, в котором находится пользователь

	TODO Хотелось бы избавиться от этой функции
	"""
	# 'user_name' состоит из имени и фамилии. Но разные пользователь по разному
	# подходят к заполнению этих полей и могут не указать имя или фамилию.
	# А если имя или фамилия отсутствуют, то обращение к ним
	# возвращает 'None', а не пустую строку. С 'user_nick' та же ситуация.
	user_name = (user.first_name or "") + " " + (user.last_name or "")
	user_nick = user.username or ""

	main_log.info(f"Inserting new user with name: {user_name} and "
				f"id:{user.id}, and in chat:{chat.title or ''} and "
				f"id:{chat.id}")

	new_user = KarmaUser.create(
				userid=user.id,
				chatid=chat.id,
				karma=0,
				user_name=user_name,
				user_nick=user_nick,
				is_freezed=False)
	new_user.save()


def change_karma(user, chat, result):
	"""
	Функция для изменения значения кармы пользователя
	:param user: пользователь, которому нужно изменить карму
	:param chat: чат, в котором находится пользователь
	:param result: на сколько нужно изменить карму
	"""
	selected_user = KarmaUser.select().where(
		(KarmaUser.chatid == chat.id) &
		(KarmaUser.userid == user.id))

	if not selected_user:
		insert_user(user, chat)

	# 'user_name' состоит из имени и фамилии. Но разные пользователь по разному
	# подходят к заполнению этих полей и могут не указать имя или фамилию.
	# А если имя или фамилия отсутствуют, то обращение к ним
	# возвращает 'None', а не пустую строку. С 'user_nick' та же ситуация.
	user_name = (user.first_name or "") + " " + (user.last_name or "")
	user_nick = user.username or ""

	main_log.info(f"Updating karma for user with name: {user_name} and " +
				f"id:{user.id}, and in chat:{chat.title or ''} and " +
				f"id:{chat.id}. Karma changed at result")

	update_user = KarmaUser.update(
							karma=(KarmaUser.karma + result),
							user_name=user_name,
							user_nick=user_nick
						).where(
							(KarmaUser.userid == user.id) &
							(KarmaUser.chatid == chat.id))
	update_user.execute()
	

@bot.message_handler(commands=["my"], func=is_my_message)
def my_karma(msg):
	"""
	Функция, которая выводит значение кармы для пользователя.
	Выводится карма для пользователя, который вызвал функцию
	:param msg: Объект сообщения-команды
	"""
	
	main_log.info("Start func 'my_karma'")
	user = select_user(msg.from_user, msg.chat)
	if not user:
		insert_user(msg.from_user, msg.chat)

	user = select_user(msg.from_user, msg.chat)

	if user.user_name:
		name = user.user_name.strip()
	else:
		name = user.user_nick.strip()

	main_log.info(f"User {name} check his karma ({user.karma})")
	user_rang = "🤖 Бот"
	if user.karma <= 9: user_rang = "🤖\n      <code>Бот</code>"
	if 10 <= user.karma < 20: user_rang = "🤫\n      <code>Тихоня</code>"
	if 20 <= user.karma < 30: user_rang = "🐛\n      <code>Личинка</code>"
	if 30 <= user.karma < 40: user_rang = "👤\n      <code>Гость</code>"
	if 40 <= user.karma < 50: user_rang = "🐤\n      <code>Прохожий</code>"
	if 50 <= user.karma < 60: user_rang = "🎗\n      <code>Новичок</code>"
	if 60 <= user.karma < 70: user_rang = "🔱\n      <code>Любопытный</code>"
	if 70 <= user.karma < 80: user_rang = "⚜️\n      <code>Странник</code>"
	if 80 <= user.karma < 90: user_rang = "✨\n      <code>Бывалый</code>"
	if 90 <= user.karma < 100: user_rang = "🥉\n      <code>Постоялец</code>"
	if 100 <= user.karma < 120: user_rang = "🥈\n      <code>Завсегдатай</code>"
	if 120 <= user.karma < 150: user_rang = "🥇\n      <code>Местный житель</code>"
	if 150 <= user.karma < 200: user_rang = "🎖\n      <code>Городовой</code>"
	if 200 <= user.karma < 250: user_rang = "🏅\n      <code>Хабаровчанин</code>"
	if 250 <= user.karma < 300: user_rang = "⭐️\n      <code>ХабАктивист</code>"
	if 300 <= user.karma < 350: user_rang = "🌟\n      <code>Дальневосточник</code>"
	if 350 <= user.karma < 400: user_rang = "🏵\n      <code>Старожил</code>"
	if 400 <= user.karma < 450: user_rang = "💫\n      <code>Сталкер</code>"
	if 450 <= user.karma < 500: user_rang = "💥\n      <code>Ветеран</code>"
	if 500 <= user.karma < 550: user_rang = "🎭\n      <code>Философ</code>"
	if 550 <= user.karma < 600: user_rang = "🎓\n      <code>Мыслитель</code>"
	if 600 <= user.karma < 650: user_rang = "🛠\n      <code>Мастер</code>"
	if 650 <= user.karma < 700: user_rang = "☀️\n      <code>Спец</code>"
	if 700 <= user.karma < 750: user_rang = "🔮\n      <code>Оракул</code>"
	if 750 <= user.karma < 800: user_rang = "🏆\n      <code>Гуру</code>"
	if 800 <= user.karma < 850: user_rang = "👑\n      <code>Элита</code>"
	if 850 <= user.karma < 900: user_rang = "🧠\n      <code>Мудрец</code>"
	if 900 <= user.karma < 1000: user_rang = "👁\n      <code>Смотритель</code>"
	if 1000 <= user.karma < 1200: user_rang = "🏹\n      <code>Вождь</code>"
	if 1200 <= user.karma < 1500: user_rang = "✝️\n      <code>Бог</code>"
	if 1500 <= user.karma < 2800: user_rang = "⚡️\n      <code>Верховный Бог</code>"
	if 1800 <= user.karma < 2000: user_rang = "⚡⚡️️️\n      <code>Пантеон</code>"
	if user.karma > 2000: user_rang = "👤\n      <code>Сломал систему</code>\n"

	now_karma = f"Карма у {name}: <b>{user.karma}</b> {user_rang}."
	bot.reply_to(msg, now_karma, parse_mode="HTML")
	bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(commands=["top"], func=is_my_message)
def top_best(msg):
	"""
	Функция которая выводит список пользователей с найбольшим значением кармы
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'top_best'")

	if len(msg.text.split()) == 1:
		result=10
	else:
		result = int(msg.text.split()[1])	
	selected_user = KarmaUser.select()\
		.where((KarmaUser.karma > 0) & (KarmaUser.chatid == msg.chat.id))\
		.order_by(KarmaUser.karma.desc())\
		.limit(result)
	user_rang = "🤖 Бот"
	top_mess = "📈 Топ благодаримых\n\n"
	for i, user in enumerate(selected_user):
		if user.user_name:
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()

		try:

			userstatus = bot.get_chat_member(msg.chat.id,user.userid)
			if userstatus.status == 'creator' or userstatus.status == 'member' or userstatus.status == 'administrator' or userstatus.status != 'left':
				if user.karma <= 9: user_rang = "🤖\n      <code>Бот</code>"
				if 10 <= user.karma < 20: user_rang = "🤫\n      <code>Тихоня</code>"
				if 20 <= user.karma < 30: user_rang = "🐛\n      <code>Личинка</code>"
				if 30 <= user.karma < 40: user_rang = "👤\n      <code>Гость</code>"
				if 40 <= user.karma < 50: user_rang = "🐤\n      <code>Прохожий</code>"
				if 50 <= user.karma < 60: user_rang = "🎗\n      <code>Новичок</code>"
				if 60 <= user.karma < 70: user_rang = "🔱\n      <code>Любопытный</code>"
				if 70 <= user.karma < 80: user_rang = "⚜️\n      <code>Странник</code>"
				if 80 <= user.karma < 90: user_rang = "✨\n      <code>Бывалый</code>"
				if 90 <= user.karma < 100: user_rang = "🥉\n      <code>Постоялец</code>"
				if 100 <= user.karma < 120: user_rang = "🥈\n      <code>Завсегдатай</code>"
				if 120 <= user.karma < 150: user_rang = "🥇\n      <code>Местный житель</code>"
				if 150 <= user.karma < 200: user_rang = "🎖\n      <code>Городовой</code>"
				if 200 <= user.karma < 250: user_rang = "🏅\n      <code>Хабаровчанин</code>"
				if 250 <= user.karma < 300: user_rang = "⭐️\n      <code>ХабАктивист</code>"
				if 300 <= user.karma < 350: user_rang = "🌟\n      <code>Дальневосточник</code>"
				if 350 <= user.karma < 400: user_rang = "🏵\n      <code>Старожил</code>"
				if 400 <= user.karma < 450: user_rang = "💫\n      <code>Сталкер</code>"
				if 450 <= user.karma < 500: user_rang = "💥\n      <code>Ветеран</code>"
				if 500 <= user.karma < 550: user_rang = "🎭\n      <code>Философ</code>"
				if 550 <= user.karma < 600: user_rang = "🎓\n      <code>Мыслитель</code>"
				if 600 <= user.karma < 650: user_rang = "🛠\n      <code>Мастер</code>"
				if 650 <= user.karma < 700: user_rang = "☀️\n      <code>Спец</code>"
				if 700 <= user.karma < 750: user_rang = "🔮\n      <code>Оракул</code>"
				if 750 <= user.karma < 800: user_rang = "🏆\n      <code>Гуру</code>"
				if 800 <= user.karma < 850: user_rang = "👑\n      <code>Элита</code>"
				if 850 <= user.karma < 900: user_rang = "🧠\n      <code>Мудрец</code>"
				if 900 <= user.karma < 1000: user_rang = "👁\n      <code>Смотритель</code>"
				if 1000 <= user.karma < 1200: user_rang = "🏹\n      <code>Вождь</code>"
				if 1200 <= user.karma < 1500: user_rang = "✝️\n      <code>Бог</code>"
				if 1500 <= user.karma < 2800: user_rang = "⚡️\n      <code>Верховный Бог</code>"
				if 1800 <= user.karma < 2000: user_rang = "⚡⚡️️️\n      <code>Пантеон</code>"
				if user.karma > 2000: user_rang = "👤\n      <code>Сломал систему</code>\n"
			

				top_mess += f"{i+1}. <b>{name}</b> ({user.karma}) {user_rang}\n"

		except Exception:
				top_mess += f"{i+1}. <b>Удаленный</b> (0) 🗑\n      <code>Покинул чат</code>\n"
#				userstatus = bot.get_chat_member(msg.chat.id,user.userid)
#				change_karma(userstatus.user, msg.chat, -100)
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="HTML")
	
	
def tinder(msg):
	"""
	Функция которая выводит пару дня
	""" 
	user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
	if user.status == 'creator':
		change_karma(msg.from_user, msg.chat, +5)
	else:
		change_karma(msg.from_user, msg.chat, -5)
	
	bot.send_chat_action(msg.chat.id, "typing")
	selected_user = KarmaUser.select()\
		.where((KarmaUser.karma > 8) & (KarmaUser.chatid == msg.chat.id))\
		.order_by(KarmaUser.karma.desc())\
		.limit(100)
	top_mess = f"🤚"
	selected_user = random.choices(selected_user)
	for i, user in enumerate(selected_user):
			
		if user.is_freezed:
			top_mess +=  f"Сегодня ночь самопознания✊"
		else:
			nick = user.user_nick.strip()
			name = user.user_name.strip()
			try:
				userstatus = bot.get_chat_member(msg.chat.id,user.userid)
				if userstatus.status == 'creator' or userstatus.status == 'member' or userstatus.status == 'administrator':
					bot.send_chat_action(msg.chat.id, "typing")
					change_karma(userstatus.user, msg.chat, random.randint(1, 3))
					top_mess = f"👫 Вы образовали пару с\n<b>{name}</b> aka @{nick} 💋 {random.randint(1, 3)} кармы."
				if userstatus.status == 'left':
					top_mess = f"👫 Вы образовали пару с\n<b>{name}</b> aka @{nick} (покинул ХабЧат), но можешь <a href='https://t.me/share/url?url=t.me/khvchat&text=Привет! Мы общаемся в Чате Хабаровска в Telegram, заходи к нам: https://t.me/khvchat'>позвать обратно</a> через личку."
			except Exception:
				top_mess+= f"Сегодня вечер самопознания🤚"
#				change_karma(userstatus.user, msg.chat, -100)

	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.reply_to(msg, top_mess, parse_mode="HTML")
	
	
def krasavchik(msg):
	"""
	Функция которая красавчика дня
	"""
	main_log.info("Starting func 'krasavchik'")
	bot.send_message(msg.chat.id, "Крутим барабан <b>ХабЧата</b>...", parse_mode="HTML")
	main_log.info("Starting func 'krasavchik'")
	bot.send_chat_action(msg.chat.id, "typing")
	selected_user = KarmaUser.select()\
		.where((KarmaUser.karma > 10) & (KarmaUser.chatid == msg.chat.id))\
		.order_by(KarmaUser.karma.desc())\
		.limit(100)
	selected_user = random.choices(selected_user)
	for i, user in enumerate(selected_user):
		if user.is_freezed:
			bot.send_message(msg.chat.id, f"🎉 Сегодня Я красавчик дня!", parse_mode="HTML")
		else:
			nick = user.user_nick.strip()
			name = user.user_name.strip()
	userstatus = bot.get_chat_member(msg.chat.id,user.userid)
	if userstatus.status == 'creator' or userstatus.status == 'member' or userstatus.status == 'administrator':
		top_mess = f"🎉 Сегодня красавчик дня:\n<b>{name}</b> aka @{nick}. 🎁 +5 кармы."
		change_karma(userstatus.user, msg.chat, 5)
	else:
		return
	if not selected_user:
		return
	bot.send_message(msg.chat.id, top_mess, parse_mode="HTML")

@bot.message_handler(commands=["pop"], func=is_my_message)
def top_bad(msg):
	"""
	Функция которая выводит список пользователей с найменьшим значением кармы
	:param msg: Объект сообщения-команды
	"""
	selected_user = KarmaUser.select() \
		.where((KarmaUser.karma < 0) & (KarmaUser.chatid == msg.chat.id)) \
		.order_by(KarmaUser.karma.asc()) \
		.limit(10)

	top_mess = "💩 Топ ругаемых:\n"
	for i, user in enumerate(selected_user):
	

		if user.user_name:
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()
		if name == "Telegram" or name == "ХабКарма":
			name =""
		
		userstatus = bot.get_chat_member(msg.chat.id,user.userid)
		if userstatus.status != 'left':
			top_mess += f"*{i+1}*. {name}, ({user.karma})\n"
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["freez", "unfreez"], func=is_my_message)
def freeze_me(msg):
	"""
	Функция, которая используется для заморозки значения кармы.
	Заморозка происходит для пользователя, вызвавшего функцию.
	Заморозка означает отключение возможности смены кармы для пользователя,
	и запрет на смену кармы другим пользователям
	:param msg: Объект сообщения-команды
	"""
	user = select_user(msg.from_user, msg.chat)
	freeze = True if msg.text[1:9] == "freez" else False

	result = ""
	if not user:
		insert_user(msg.from_user, msg.chat)
		user = select_user(msg.from_user, msg.chat)
	if user.is_freezed != freeze:
		result += "Статус изменен. "
		KarmaUser.update(is_freezed=(not user.is_freezed)).where(
			(KarmaUser.userid == msg.from_user.id) &
			(KarmaUser.chatid == msg.chat.id)).execute()
	result += f"Текущий статус: карма {'за' if freeze else 'раз'}морожена."
	bot.reply_to(msg, result)


@bot.message_handler(commands=["god"])
def gods(msg):
	"""
	Небольшая функция, которая позволяет создателю бота 
	добавить кому и сколько угодно очков кармы в обход 
	всех ограничений.
	:param msg: Объект сообщения-команды
	"""
	if len(msg.text.split()) == 1:
		return

	if msg.from_user.id not in config.gods:
		bot.reply_to(msg, "Ты не имеешь власти.")
		return
	result = int(msg.text.split()[1])
	change_karma(msg.reply_to_message.from_user, msg.chat, result)
	bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(commands=["gift"])
def gift_karma(msg):
	"""
	Небольшая функция, которая позволяет создателю бота 
	добавить подарок
	"""
	if is_game_abuse(msg):
		return
	if is_karma_freezed(msg):
		return
	if msg.reply_to_message:
		if msg.from_user.id == msg.reply_to_message.from_user.id:
			bot.send_message(msg.chat.id, "Нельзя изменять карму самому себе.")
			return
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
		if user.status == 'administrator' or user.status == 'creator':
			change_karma(msg.reply_to_message.from_user, msg.chat, 5)
			bot.reply_to(msg, "🎁 отсыпал кармы")
		else:
			user = select_user(msg.from_user, msg.chat)
			if not user:
				insert_user(msg.from_user, msg.chat)
			user = select_user(msg.from_user, msg.chat)
			if user.karma > 5:
				bot.send_chat_action(msg.chat.id, "typing")
				change_karma(msg.from_user, msg.chat, -5)
				change_karma(msg.reply_to_message.from_user, msg.chat, 5) 
				bot.reply_to(msg.reply_to_message, "🎁 Вам подарили карму: <b>+5</b>.", parse_mode="HTML")
				
			else:
				bot.send_chat_action(msg.chat.id, "typing")
				bot.reply_to(msg, "🎁 Нехватает кармы для подарка.", parse_mode="HTML")
	else:
		return

@bot.message_handler(commands=["unmute"], func=is_my_message)
def un_mute(msg):
	"""
	Команда для создателя. Позволяет снять с 1-го пользователя ограничение
	на изменение кармы
	:param msg: Объект сообщения-команды
	"""
	if msg.from_user.id not in config.gods:
		return
	Limitation.delete().where(
		(Limitation.userid == msg.reply_to_message.from_user.id) &
		(Limitation.chatid == msg.chat.id)).execute()
	bot.send_message(msg.chat.id, "Возможность менять карму возвращена.")

def is_karma_changing(text):
	result = []
	# Проверка изменения кармы по смайликам
	if len(text) == 1:
		if text in config.good_emoji:
			result.append(1)
		if text in config.bad_emoji:
			result.append(-1)
		return result

	# Обработка текста для анализа
	text = text.lower()
	for punc in string.punctuation:
		text = text.replace(punc, "")
	for white in string.whitespace[1:]:
		text = text.replace(white, "")

	# Проверка изменения кармы по тексту сообщения
	for word in config.good_words:
		if word == text \
				or (" "+word+" " in text) \
				or text.startswith(word) \
				or text.endswith(word):
			result.append(1)

	for word in config.bad_words:
		if word in text \
				or (" "+word+" " in text) \
				or text.startswith(word) \
				or text.endswith(word):
			result.append(-1)
	return result


def is_karma_changing_mat(text):
	result = []
		
	if len(text)==1:
		result.append(-1)

			# Обработка текста для анализа
	text = text.lower()
	for punc in string.punctuation:
		text = text.replace(punc, "")
	for white in string.whitespace[1:]:
		text = text.replace(white, "")
		
	for word in config.mat_words:
		if word in text \
				or (" "+word+" " in text) \
				or text.startswith(word) \
				or text.endswith(word):
			result.append(-1)
	if len(text.split()) > 2:
		for word in config.heppy_words:
			if word in text \
					or (" "+word+" " in text) \
					or text.startswith(word) \
					or text.endswith(word):
				result.append(1)
			

	return result

def is_karma_freezed(msg):
	"""
	Функция для проверки индивидуальной блокировки кармы.
	:param msg: Объект собщения, из которого берутся id чата и пользователей
	:return: True если у кого-то из учасников заморожена карма. Иначе False.
	"""

	# Выборка пользователей, связаных с сообщением.
	banned_request = KarmaUser.select().where(
		(KarmaUser.chatid == msg.chat.id) &
		(
			(KarmaUser.userid == msg.from_user.id) |
			(KarmaUser.userid == msg.reply_to_message.from_user.id)
		)
	)

	# У выбраных пользователей проверяется статус заморозки
	for req in banned_request:
		if req.is_freezed:
			name = ""
			if not req.user_name.isspace():
				name = req.user_name.strip()
			else:
				name = req.user_nick.strip()
			# Сообщение, у кого именно заморожена карма
#			reply_text = f"Юзер: {name}.\nСтатус кармы: Заморожена."
#			bot.send_message(msg.chat.id, reply_text)
			return True
	return False


def is_game_abuse(msg):
	user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
	if user.status == 'creator':
		return
	hours_ago_12 = pw.SQL(f"current_timestamp-interval'{random.randint(10, 120)} minutes'")
	limitation_request = Limitation.select().where(
		(Limitation.timer > hours_ago_12) &
		(Limitation.userid == msg.from_user.id) &
		(Limitation.chatid == msg.chat.id))

	if len(limitation_request) > 0:
		timer = limitation_request[0].timer + datetime.timedelta(hours=15)
		timer = timer.strftime("%H:%M %d.%m.%Y")
		bot.delete_message(msg.chat.id, msg.message_id)
		return True
	return False
	
def is_karma_abuse(msg):
	user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
	if user.status == 'creator':
		return
	hours_ago_12 = pw.SQL(f"current_timestamp-interval'{random.randint(5, 60)} minutes'")
	limitation_request = Limitation.select().where(
		(Limitation.timer > hours_ago_12) &
		(Limitation.userid == msg.from_user.id) &
		(Limitation.chatid == msg.chat.id))

	if len(limitation_request) > 1:
		timer = limitation_request[0].timer + datetime.timedelta(hours=15)
		timer = timer.strftime("%H:%M %d.%m.%Y")
		return True
	return False

#@bot.poll_answer_handler()
#def pola(polle):
#	bot.send_poll(msg.chat.id, 'Это опрос?', ['Да', 'Нет', 'Не знаю'])
#	bot.send_message(msg, polle, parse_mode="HTML")
			
def commands(msg, text):
	
	main_log.info("Starting func 'commands'")

	if 'бот ' in msg.text.lower() or ' бот' in msg.text.lower() or 'скуч' in msg.text.lower():
		bot.send_chat_action(msg.chat.id, "typing")
		bot.reply_to(msg, f"{random.choice(config.bot_words)}", parse_mode="HTML")

	if 'бот фильм' in msg.text.lower() or ' бот фильм' in msg.text.lower():
		bot.send_chat_action(msg.chat.id, "typing")
		bot.reply_to(msg, f"{random.choice(config.bot_film)}", parse_mode="HTML")

	if '!? ' in msg.text.lower():
		bot.send_chat_action(msg.chat.id, "typing")
		random_karma = ("Абсолютно точно!","Да.","Нет.","Скорее да, чем нет.","Не уверен...","Однозначно нет!","Если ты не фанат аниме, у тебя все получится!","Можешь быть уверен в этом.","Перспективы не очень хорошие.","А как же иначе?.","Да, но если только ты не смотришь аниме.","Знаки говорят - да.","Не знаю.","Мой ответ - нет.","Весьма сомнительно.","Не могу дать точный ответ.")
		random_karma2 = random.choice(random_karma)
		bot.reply_to(msg, f"🔮 {random_karma2}", parse_mode="HTML")
	if '!v ' in msg.text.lower():
		result = msg.text.lower()
		result = result.replace(msg.text.split()[0], "")
		bot.send_poll(msg.chat.id, f'{result}❓', ['Да!', 'Нет.', 'Не знаю.'])
		
	if ' vs ' in msg.text.lower():
		bot.send_chat_action(msg.chat.id, "typing")
		random_karma = ("2️⃣ Определенно второе","1️⃣ Определенно первое")
		random_karma2 = random.choice(random_karma)
		bot.reply_to(msg, f"🔮 {random_karma2}", parse_mode="HTML")
		
	if 'love' in msg.text.lower():
		loves_text = "<a href='tg://user?id=55910350'>❤</a>️ Ваше объявление будет размещено в Знакомствах: @love_khv"
		bot.reply_to(msg, loves_text, parse_mode="HTML")
	
	if msg.text.lower() in ['язабан']:
		user = bot.get_chat_member(msg.chat.id, msg.reply_to_message.from_user.id)
		if user.status == 'administrator' or user.status == 'creator':
			return
		if msg.reply_to_message:
			bot.send_message(msg.chat.id, f"<a href='tg://user?id=55910350'>🔫</a> <b>{msg.from_user.first_name}</b> предлагает выгнать <b>{msg.reply_to_message.from_user.first_name}</b> из Хабчата!", parse_mode="HTML")
			bot.send_poll(msg.chat.id, f'Согласны выгнать {msg.reply_to_message.from_user.first_name} из Чата?', ['Да', 'Нет', 'Не знаю'],is_anonymous=False)
		else:
			return
	
	if msg.text.lower() in ['!k']:
		bot.delete_message(msg.chat.id, msg.message_id)
		user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
		if user.status == 'creator':
			krasavchik(msg)

	if msg.text.lower() in ['цитата']:
		citata = random.choice(config.citata_words)
		bot.send_chat_action(msg.chat.id, "typing")
		bot.reply_to(msg, f"📍 Цитата: {citata}", parse_mode="HTML")
		

	if msg.text.lower() in ['купить']:
		keyboard = types.InlineKeyboardMarkup()
		url_button = types.InlineKeyboardButton(text="💰 Купить кармы - 1р.", url="https://khabara.ru/informer.html")
		keyboard.add(url_button)
		bot.send_message(msg.chat.id, "Вы можете купить карму, оплатив по кнопке ниже.", reply_markup=keyboard)
		
	if ' чат ' in msg.text.lower():
		keyboard = types.InlineKeyboardMarkup()
		url_button1 = types.InlineKeyboardButton(text="TG", url="https://t.me/share/url?url=t.me/khvchat&text=Привет! Мы общаемся в Чате Хабаровска в Telegram, заходи к нам: https://t.me/khvchat")
		url_button2 = types.InlineKeyboardButton(text="WA", url="https://api.whatsapp.com/send?text=Привет! Мы общаемся в Чате Хабаровска в Telegram, заходи к нам: https://t.me/khvchat")
		url_button3 = types.InlineKeyboardButton(text="ВК", url="https://vk.com/share.php?url=https://t.me/khvchat&title=Привет! Мы общаемся в Чате Хабаровска в Telegram, заходи к нам: https://t.me/khvchat")
		
		url_button4 = types.InlineKeyboardButton(text="ОК", url="https://connect.ok.ru/offer?url=https://t.me/khvchat&title=Привет! Мы общаемся в Чате Хабаровска в Telegram, заходи к нам: https://t.me/khvchat")
		
		keyboard.row(url_button1, url_button2, url_button3, url_button4)
		bot.send_message(msg.chat.id, "💬 Пригласи в ХабЧат друзей из других мессенджеров:", reply_markup=keyboard)
		
		
	if msg.text.lower() in ['утра']:
		bot.send_chat_action(msg.chat.id, "typing")
		citata = random.choice(config.citata_words)
		bot.reply_to(msg, f"С добрым утром, Хабаровск! ☀️ Вам отличного и позитивного настроения!!!", parse_mode="HTML")

	if msg.text.lower() in ['превед']:
		if msg.reply_to_message:
			bot.send_chat_action(msg.chat.id, "typing")
			bot.reply_to(msg.reply_to_message,f"✌Приветствуем тебя в <b>ХабЧате</b>! По доброй традиции, желательно представиться и рассказать немного о себе.", parse_mode="HTML")
		else:
			return
	if msg.text.lower() in ['сохранить'] or msg.text.lower() in ['save']:
		if msg.reply_to_message:
			bot.send_chat_action(msg.chat.id, "typing")
			bot.forward_message(-1001338159710, msg.chat.id, msg.reply_to_message.message_id)
			bot.reply_to(msg.reply_to_message,f"💾 Сообщение сохранено в <a href='https://t.me/joinchat/T8KyXgxSk1o4s7Hk'>Цитатник ХабЧата</a>.", parse_mode="HTML")
		else:
			return
	if msg.text.lower() in ['фото']:
		if msg.reply_to_message:
			bot.send_chat_action(msg.chat.id, "typing")
			bot.reply_to(msg.reply_to_message,f"Не соблаговолите ли вы скинуть в чат свою фоточку, нам будет очень приятно вас лицезреть 🙂", parse_mode="HTML")
		else:
			return
	if msg.text.lower() in ['фсб']:
		if msg.reply_to_message:
			bot.send_chat_action(msg.chat.id, "typing")
			bot.reply_to(msg.reply_to_message,f"<a href='https://telegra.ph/file/1a296399c86ac7a19777f.jpg'>😎</a> За вами уже выехали!", parse_mode="HTML")
		else:
			return
	if msg.text.lower() in ['войс']:
		if msg.reply_to_message:
			bot.reply_to(msg.reply_to_message,f"🔔🔔🔔🔔🔔🔔🔔\n🗣Го в Войс Чат!👂\
\n🔔🔔🔔🔔🔔🔔🔔", parse_mode="HTML")
		else:
			bot.send_message(msg.chat.id, f"🔔🔔🔔🔔🔔🔔🔔\n🗣Го в Войс Чат!👂\
\n🔔🔔🔔🔔🔔🔔🔔", parse_mode="HTML")

	if '!к ' in msg.text.lower():
		
		result = msg.text.split()[1].lower()
		bot.send_message(msg.chat.id,f'🐊 {msg.from_user.first_name} загадал(а) свое слово.', parse_mode="HTML")
		saves_database[database] = result
		bot.send_message(-1001110839896,f'🐊 {msg.from_user.first_name} загадал(а) свое слово.', parse_mode="HTML")
#		bot.forward_message(-1001110839896, msg.message_id)
		bot.delete_message(msg.chat.id, msg.message_id)

	if msg.text.lower() in ['крокодил'] or msg.text.lower() in ['/croco@khabara_bot'] or msg.text.lower() in ['/croco']:
		a=random.randint(1,1000)
		idmy =a+msg.from_user.id
		idmy2 =idmy+1
		idmy3=idmy+3
		saves_database_time[database_time] =a
		saves_database_id[database_id] =f"{msg.from_user.id}"
		saves_database[database] = random.choice(config.kroko_words)
		bot.send_chat_action(msg.chat.id, "typing")
		markup = telebot.types.InlineKeyboardMarkup()
		
		button = telebot.types.InlineKeyboardButton(text='👀', callback_data=idmy)
		button3 = telebot.types.InlineKeyboardButton(text='🐊', callback_data=idmy3)
		button2 = telebot.types.InlineKeyboardButton(text='🔄', callback_data=idmy2)
		button4 = telebot.types.InlineKeyboardButton(text='ℹ️', callback_data=idmy2)
		markup.add(button,button2,button3,button4)
		bot.send_message(chat_id=msg.chat.id, text=f'🐊 {msg.from_user.first_name} загадал(а) слово в игре Крокодил.', reply_markup=markup)
		bot.delete_message(msg.chat.id, msg.message_id)
	seves = saves_database.get(database)
	seves_id = saves_database_id.get(database_id)
	seves_time = saves_database_time.get(database_time)

	if re.search(r'[а-яА-ЯёЁ]',msg.text.split()[0].lower()) and re.search(r'[A-Za-z]',msg.text.split()[0].lower()):
		bot.reply_to(msg,f"Попытался обойти систему 🗿", parse_mode="HTML")
	if msg.text.lower() == seves:
		if seves_id ==  f"{msg.from_user.id}":
					bot.send_chat_action(msg.chat.id, "typing")
					bot.reply_to(msg,f"Мухлевать не красиво: -10 кармы 💩", parse_mode="HTML")
					change_karma(msg.from_user, msg.chat, -10)
					
		else:
			bot.send_chat_action(msg.chat.id, "typing")
			bot.reply_to(msg,f"🎉 Правильный ответ: <b>{seves}</b> +3 кармы, запустить игру /croco", parse_mode="HTML")
			change_karma(msg.from_user, msg.chat, 3)
			saves_database[database] = "dse4f"

#	if msg.text.lower() in ['играть']:

#		markup = telebot.types.InlineKeyboardMarkup()
#		button = telebot.types.InlineKeyboardButton(text='играть', callback_data="pravda")
#		markup.add(button)
#		bot.send_message(chat_id=msg.chat.id, text=f'🐊 {msg.from_user.first_name} загадал слово.', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
	seves_time = saves_database_time.get(database_time)
	idmy =seves_time+call.from_user.id
	idmy2=idmy+1
	idmy3=idmy+3
	if  f"{idmy}" == f"{call.data}":
		bot.answer_callback_query(callback_query_id=call.id, show_alert=True,  text=f"Задуманное слово: {saves_database[database]}")

	if f"{idmy3}" == f"{call.data}":
		saves_database[database] = random.choice(["🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🐯","🦁","🐮","🐷","🐽","🐸","🐵","🙈","🙉","🙊","🙊","🐒","🐔","🐧","🐦","🐤","🐣","🐥","🦆","🦅","🦉","🦇","🐺","🐗","🐴","🦄","🐝","🪱","🐛","🦋","🐌","🐞","🐜","🪰","🪲","🪳","🦟","🦗","🕷","🕸","🦂","🐢","🐍","🦎","🦖","🦕","🐙","🦑","🦐","🦞","🦀","🐡","🐠","🐟","🐬","🐳","🐋","🦈","🐊","🐅","🐆","🦓","🦍","🦧","🐘","🦛","🦏","🐪","🐫","🦒","🦘","🐃","🐂","🐄","🐎","🐖","🐏","🐑","🦙","🐐","🦌","🐕","🐩","🦮","🐈","🐓","🦃","🦚","🦜","🦢","🦩","🕊","🐇","🦝","🦨","🦡","🦦","🦥","🐁","🐀","🐿","🦔","🐾","🐉","🐲"])
		bot.answer_callback_query(callback_query_id=call.id, show_alert=True,  text=f"Задуманное Эмодзи: {saves_database[database]}")
		bot.send_message(call.message.chat.id, f"🐊 {call.from_user.first_name} загадал <b>Эмодзи</b>", parse_mode="HTML")
		
	if f"{idmy2}" == f"{call.data}":
		saves_database[database] = random.choice(config.kroko_words)
		bot.answer_callback_query(callback_query_id=call.id, show_alert=True,  text=f"Задуманное слово: {saves_database[database]}")
		bot.send_message(call.message.chat.id, f"🐊 {call.from_user.first_name} сменил слово -5 кармы", parse_mode="HTML")
#	if  call.data == "pravda":
#		bot.delete_message(call.id, call.message_id)
		
	if  f"{idmy2}" != f"{call.data}":
		bot.answer_callback_query(callback_query_id=call.id, show_alert=True,  text=f"Слово знает только тот кто стартовал игру.")
		
  
def reputation(msg, text):
	""" TODO """

	# Если сообщение большое, то прервать выполнение функции
	if len(text) > 100:
		return

	# Если карму не пытаются изменить, то прервать выполнение функции
	how_much_changed = is_karma_changing(text)
	if not how_much_changed:
		return

	# При попытке поднять карму самому себе прервать выполнение функции
	if msg.from_user.id == msg.reply_to_message.from_user.id:
		bot.send_message(msg.chat.id, "Нельзя изменять карму самому себе.")
		return

	# Ограничение на изменение кармы для пользователя во временной промежуток
	if is_karma_abuse(msg):
		return

	if is_karma_freezed(msg):
		return
	# Если значение кармы все же можно изменить: изменяем
	result = sum(how_much_changed)
	if result != 0:
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		change_karma(msg.reply_to_message.from_user, msg.chat, result)

	if result > 0:
		res = "повышена ⬆️"
	elif result < 0:
		res = "понижена ⬇️"
	else:
		res = "не изменена"

	user = KarmaUser.select().where(
		(KarmaUser.userid == msg.reply_to_message.from_user.id) &
		(KarmaUser.chatid == msg.chat.id)).get()

	if not user.user_name.isspace():
		name = user.user_name.strip()
	else:
		name = user.user_nick.strip()
		
	if name == "Telegram" or name == "ХабКарма":
		return

	now_karma = f"Карма {res}.\n{name}: <b>{user.karma}</b>."
	bot.send_message(msg.chat.id, now_karma, parse_mode="HTML")

def reputation_mat(msg, text):
	""" TODO понижение репутации за маты"""
	
	how_much_changed = is_karma_changing_mat(text)
	if not how_much_changed:
		return
	# Если значение кармы все же можно изменить: изменяем
	result = sum(how_much_changed)
	if result != 0:
		change_karma(msg.from_user, msg.chat, result)
		

def reply_exist(msg):
	return msg.reply_to_message


@bot.message_handler(content_types=["text"], func=reply_exist)
def changing_karma_text(msg):
	if msg.chat.type == "private":
		return
	reputation(msg, msg.text)
	reputation_mat(msg, msg.text)
	commands(msg, msg.text)
	

@bot.message_handler(content_types=["sticker"], func=reply_exist)
def changing_karma_sticker(msg):
	if msg.chat.type == "private":
		return
	reputation(msg, msg.sticker.emoji)
	
@bot.message_handler(content_types=['text'])	
def karma_game(msg):
	if msg.chat.type == "private":
		return
	reputation_mat(msg, msg.text)
	commands(msg, msg.text)
	"""
	Функция играть в карму.
	"""
	if msg.text.lower() in ['тиндер']:
		if is_game_abuse(msg):
			return
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		user = select_user(msg.from_user, msg.chat)
		if not user:
			insert_user(msg.from_user, msg.chat)
		user = select_user(msg.from_user, msg.chat)	
		if user.is_freezed:
			bot.reply_to(msg, f"Разморозьте карму чтобы играть!", parse_mode="HTML")
		else:
			if user.karma > 10:
					tinder(msg)
			else:
				bot.delete_message(msg.chat.id, msg.message_id)
				
				
@bot.message_handler(content_types=['dice'])
def send_dice(msg):
	if msg.chat.type == "private":
		return
	if msg.forward_from != None:
		bot.delete_message(msg.chat.id, msg.message_id)
	else:
		if is_game_abuse(msg):
			return
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		user = select_user(msg.from_user, msg.chat)
		if not user:
			insert_user(msg.from_user, msg.chat)
		user = select_user(msg.from_user, msg.chat)	
		if user.is_freezed:
			bot.reply_to(msg, f"Разморозьте карму чтобы играть!", parse_mode="HTML")
		else:
			if user.karma > msg.dice.value:
				bot.send_chat_action(msg.chat.id, "typing")
				random_karma = ("-","+")
				random_karma2 = random.choice(random_karma)
				bot.send_chat_action(msg.chat.id, "typing")
				bot.reply_to(msg, f"Сыграл в карму {random_karma2}{msg.dice.value}", parse_mode="HTML")
				user = bot.get_chat_member(msg.chat.id, msg.from_user.id)
				if user.status == 'creator':
					change_karma(msg.from_user, msg.chat, f"+{msg.dice.value}")
				else:
					change_karma(msg.from_user, msg.chat, f"{random_karma2}{msg.dice.value}")
			else:
				bot.delete_message(msg.chat.id, msg.message_id)

# bot.polling(none_stop=True)


# Дальнейший код используется для установки и удаления вебхуков
server = Flask(__name__)


@server.route("/bot", methods=['POST'])
def get_message():
	""" TODO """
	decode_json = request.stream.read().decode("utf-8")
	bot.process_new_updates([telebot.types.Update.de_json(decode_json)])
	return "!", 200


@server.route("/")
def webhook_add():
	""" TODO """
	bot.remove_webhook()
	bot.set_webhook(url=config.url)
	return "!", 200

@server.route("/<password>")
def webhook_rem(password):
	""" TODO """
	password_hash = hashlib.md5(bytes(password, encoding="utf-8")).hexdigest()
	if password_hash == "5b4ae01462b2930e129e31636e2fdb68":
		bot.remove_webhook()
		return "Webhook removed", 200
	else:
		return "Invalid password", 200


server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

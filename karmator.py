#!usr/bin/python3
import datetime
import hashlib
import string
import os
import random

from flask import Flask, request
import peewee as pw
import telebot

from database import KarmaUser, Limitation
from logger import main_log
import config

main_log.info("Program starting")
TELEGRAM_API = os.environ["telegram_token"]
bot = telebot.TeleBot(TELEGRAM_API)


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


@bot.message_handler(commands=["karma"], func=is_my_message)
def helps(msg):
	"""
	Функция для отправки списка общедоступных команд для бота
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'help'")

	bot.send_chat_action(msg.chat.id, "typing")

	help_mess = "Выражения похвалы повышают карму, ругательства понижают.\
	\nОграничения на выдачу кармы: 7 раз в 12 часов.\
	\n\nКомманды:\
	\n/my Для просмотра своей кармы.\
	\n/top Узнать наиболее благодаримых в чате. \
	\n/pop Узнать наиболее ругаемых в чате. \
	\n/weather Погода. \
	\n/no - Для объявлений \
	\n/report - Отправить жалобу"
	bot.send_message(msg.chat.id, help_mess)

@bot.message_handler(commands=["weather"], func=is_my_message)
def source(msg):
	"""
	Функция, которая по запросу возвращает ссылку на гитхаб-репозиторий,
	в котором хранится исходный код бота
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'source'") 
	reply_text = "<a href=\"https://t.me/iv?url=https://khabara.ru/weather.php&rhash=c036525856601d\">погода</a>"
	bot.reply_to(msg, reply_text, parse_mode="HTML")
	
@bot.message_handler(commands=["report"], func=is_my_message)
def report(msg):
	"""
	Функция, для жалоб админам
	"""
	main_log.info("Starting func 'report'")
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
	if msg.reply_to_message:
		bot.reply_to(msg.reply_to_message,nos_text)
	else:
		bot.reply_to(msg,nos_text)
		
@bot.message_handler(commands=["love"], func=is_my_message)
def loves(msg):
	"""
	Функция, для Знакомства
	"""
	main_log.info("Starting func 'loves'") 
	loves_text = "❤️ Ваше объявление будет размещено в Знакомствах @love_khv \n\n@jcrush"
  if msg.reply_to_message:
    bot.reply_to(msg.reply_to_message, loves_text)
  else:
    bot.reply_to(msg.reply_to_message,"Чтобы подать объявление о Знакомстве напишите /love и осмысленный текст О себе и т.д.")

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

	if user.user_name.isspace():
		name = user.user_name.strip()
	else:
		name = user.user_nick.strip()

	main_log.info(f"User {name} check his karma ({user.karma})")
	user_rang = "🤖 Бот"
	if user.karma <= 9: user_rang = "🤖 Бот"
	if 10 <= user.karma < 20: user_rang = "🤫 Тихоня"
	if 20 <= user.karma < 30: user_rang = "🐛 Личинка"
	if 30 <= user.karma < 40: user_rang = "👤 Гость"
	if 40 <= user.karma < 50: user_rang = "🐤 Прохожий"
	if 50 <= user.karma < 60: user_rang = "🎗 Новичок"
	if 60 <= user.karma < 70: user_rang = "🔱 Любопытный"
	if 70 <= user.karma < 80: user_rang = "⚜️ Странник"
	if 80 <= user.karma < 90: user_rang = "✨ Бывалый"
	if 90 <= user.karma < 100: user_rang = "🥉 Постоялец"
	if 100 <= user.karma < 110: user_rang = "🥈 Завсегдатай"
	if 110 <= user.karma < 120: user_rang = "🥇 Местный житель"
	if 120 <= user.karma < 130: user_rang = "🎖 Городовой"
	if 130 <= user.karma < 140: user_rang = "🏅 Хабаровчанин"
	if 140 <= user.karma < 150: user_rang = "⭐️ ХабАктивист "
	if 150 <= user.karma < 160: user_rang = "🌟 Дальневосточник"
	if 160 <= user.karma < 170: user_rang = "🏵 Старожил"
	if 170 <= user.karma < 180: user_rang = "💫 Сталкер"
	if 180 <= user.karma < 190: user_rang = "💥 Ветеран"
	if 190 <= user.karma < 200: user_rang = "🎭 Философ"
	if 200 <= user.karma < 210: user_rang = "🎓 Мыслитель"
	if 210 <= user.karma < 220: user_rang = "🛠 Мастер"
	if 220 <= user.karma < 230: user_rang = "☀️ Спец"
	if 230 <= user.karma < 240: user_rang = "🔮 Оракул"
	if 240 <= user.karma < 250: user_rang = "🏆 Гуру"
	if 250 <= user.karma < 260: user_rang = "👑 Элита"
	if 260 <= user.karma < 270: user_rang = "🧠 Мудрец"
	if 270 <= user.karma < 280: user_rang = "👁 Смотритель"
	if 280 <= user.karma < 290: user_rang = "✝️ Бог"
	if 290 <= user.karma < 300: user_rang = "⚡️ Верховный Бог"
	if 300 <= user.karma < 9999: user_rang = "👤 Сломал систему"

	now_karma = f"Карма у {name}: <b>{user.karma}</b> {user_rang}."
	bot.reply_to(msg, now_karma, parse_mode="HTML")

@bot.message_handler(commands=["top"], func=is_my_message)
def top_best(msg):
	"""
	Функция которая выводит список пользователей с найбольшим значением кармы
	:param msg: Объект сообщения-команды
	"""
	main_log.info("Starting func 'top_best'")
 
	selected_user = KarmaUser.select()\
		.where((KarmaUser.karma > 0) & (KarmaUser.chatid == msg.chat.id))\
		.order_by(KarmaUser.karma.desc())\
		.limit(10)
	user_rang = "🤖 Бот"
	top_mess = "🏆 Топ благодаримых\n\n"
	for i, user in enumerate(selected_user):
		if user.karma <= 9: user_rang = "🤖 Бот"
		if 10 <= user.karma < 20: user_rang = "🤫 Тихоня"
		if 20 <= user.karma < 30: user_rang = "🐛 Личинка"
		if 30 <= user.karma < 40: user_rang = "👤 Гость"
		if 40 <= user.karma < 50: user_rang = "🐤 Прохожий"
		if 50 <= user.karma < 60: user_rang = "🎗 Новичок"
		if 60 <= user.karma < 70: user_rang = "🔱 Любопытный"
		if 70 <= user.karma < 80: user_rang = "⚜️ Странник"
		if 80 <= user.karma < 90: user_rang = "✨ Бывалый"
		if 90 <= user.karma < 100: user_rang = "🥉 Постоялец"
		if 100 <= user.karma < 110: user_rang = "🥈 Завсегдатай"
		if 110 <= user.karma < 120: user_rang = "🥇 Местный житель"
		if 120 <= user.karma < 130: user_rang = "🎖 Городовой"
		if 130 <= user.karma < 140: user_rang = "🏅 Хабаровчанин"
		if 140 <= user.karma < 150: user_rang = "⭐️ ХабАктивист "
		if 150 <= user.karma < 160: user_rang = "🌟 Дальневосточник"
		if 160 <= user.karma < 170: user_rang = "🏵 Старожил"
		if 170 <= user.karma < 180: user_rang = "💫 Сталкер"
		if 180 <= user.karma < 190: user_rang = "💥 Ветеран"
		if 190 <= user.karma < 200: user_rang = "🎭 Философ"
		if 200 <= user.karma < 210: user_rang = "🎓 Мыслитель"
		if 210 <= user.karma < 220: user_rang = "🛠 Мастер"
		if 220 <= user.karma < 230: user_rang = "☀️ Спец"
		if 230 <= user.karma < 240: user_rang = "🔮 Оракул"
		if 240 <= user.karma < 250: user_rang = "🏆 Гуру"
		if 250 <= user.karma < 260: user_rang = "👑 Элита"
		if 260 <= user.karma < 270: user_rang = "🧠 Мудрец"
		if 270 <= user.karma < 280: user_rang = "👁 Смотритель"
		if 280 <= user.karma < 290: user_rang = "✝️ Бог"
		if 290 <= user.karma < 300: user_rang = "⚡️ Верховный Бог"
		if 300 <= user.karma < 9999: user_rang = "👤 Сломал систему"
		if user.user_name:
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()
			
		top_mess += f"*{i+1}*. {name} ({user.karma}) {user_rang}\n"
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="Markdown")


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
		top_mess += f"*{i+1}*. {name}, ({user.karma})\n"
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["freezeme", "unfreezeme"], func=is_my_message)
def freeze_me(msg):
	"""
	Функция, которая используется для заморозки значения кармы.
	Заморозка происходит для пользователя, вызвавшего функцию.
	Заморозка означает отключение возможности смены кармы для пользователя,
	и запрет на смену кармы другим пользователям
	:param msg: Объект сообщения-команды
	"""
	user = select_user(msg.from_user, msg.chat)
	freeze = True if msg.text[1:9] == "freezeme" else False

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


@bot.message_handler(commands=["gods_intervention"])
def gods_intervention(msg):
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


@bot.message_handler(commands=["the_gods_says"])
def the_gods_says(message):
	"""
	Если от лица создателя чата нужно что-то сказать во 
	все чаты, где используется бот.
	TODO Или дописать, или удалить.
	"""
	if message.from_user.id not in config.gods:
		return


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
			reply_text = f"Юзер: {name}.\nСтатус кармы: Заморожена."
			bot.send_message(msg.chat.id, reply_text)
			return True
	return False


def is_karma_abuse(msg):
	hours_ago_12 = pw.SQL("current_timestamp-interval'12 hours'")
	limitation_request = Limitation.select().where(
		(Limitation.timer > hours_ago_12) &
		(Limitation.userid == msg.from_user.id) &
		(Limitation.chatid == msg.chat.id))

	if len(limitation_request) > 10:
		timer = limitation_request[0].timer + datetime.timedelta(hours=15)
		timer = timer.strftime("%H:%M:%S %d.%m.%Y")
		#reply_text = f"Возможность изменять карму будет доступна с: {timer}"
		#bot.send_message(msg.chat.id, reply_text)
		return True
	return False


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

	bot.send_chat_action(msg.chat.id, "typing")

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

	now_karma = f"Карма {res}.\n{name}: <b>{user.karma}</b>."
	bot.send_message(msg.chat.id, now_karma, parse_mode="HTML")


def reply_exist(msg):
	return msg.reply_to_message


@bot.message_handler(content_types=["text"], func=reply_exist)
def changing_karma_text(msg):
	reputation(msg, msg.text)

@bot.message_handler(content_types=["sticker"], func=reply_exist)
def changing_karma_sticker(msg):
	reputation(msg, msg.sticker.emoji)
	
@bot.message_handler(content_types=['text'])	
def send_text(msg):
	"""
	Функция играть в карму.
	"""
	if is_karma_abuse(msg):
		return
	
	elif msg.text.lower() == 'играть':
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		random_karma = ("+1", "-1", "-2", "+2", "+3", "-3", "+4", "-4", "+5", "-5")
		random_karma2 = random.choice(random_karma)
		change_karma(msg.from_user, msg.chat, random_karma2)
		random_karma3 = f"🎲 Сыграл в карму: <b>{random_karma2}</b>."
		bot.reply_to(msg, random_karma3, parse_mode="HTML")

	

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
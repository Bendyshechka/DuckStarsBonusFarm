import asyncio
import re
import random
import aiohttp
import json
import time
import os
from telethon import TelegramClient, events, connection
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.errors import FloodWaitError

# --- ЗАГРУЗКА КОНФИГА ---
CONFIG_FILE = 'config.json'


def load_config():
    """Загружает конфигурацию из JSON-файла."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Проверка обязательных полей
        required = ['api_id', 'api_hash', 'recipient', 'bot_token', 'group_id']
        missing = [field for field in required if not config.get(field)]

        if missing:
            print(f"❌ Ошибка: В config.json отсутствуют поля: {', '.join(missing)}")
            print("Запустите config_setup.py для настройки.")
            exit(1)

        # Обеспечиваем наличие секции proxy
        if 'proxy' not in config:
            config['proxy'] = {
                "enabled": False,
                "server": "",
                "port": 0,
                "secret": ""
            }

        return config
    except FileNotFoundError:
        print("❌ Файл config.json не найден!")
        print("Создайте его вручную или запустите config_setup.py")
        exit(1)
    except json.JSONDecodeError:
        print("❌ Ошибка чтения config.json: неверный формат JSON")
        exit(1)


config = load_config()

# --- ПРИМЕНЕНИЕ НАСТРОЕК ИЗ КОНФИГА ---
API_ID = config['api_id']
API_HASH = config['api_hash']
RECIPIENT = config['recipient']
BOT_TOKEN = config['bot_token']
GROUP_ID = config['group_id']

# --- НАСТРОЙКА ПРОКСИ ---
PROXY_ENABLED = config['proxy'].get('enabled', False)
PROXY_SERVER = config['proxy'].get('server', '')
PROXY_PORT = config['proxy'].get('port', 0)
PROXY_SECRET = config['proxy'].get('secret', '')

SESSION_NAME = 'duck_farm_session'

# НАСТРОЙКИ ФЕРМЫ (неизменяемые)
TARGET_BOTS = ['duckearnbot', 'KtoTutRobot']
CLEAN_BIO = "Обычное био человека"
STATE_FILE = 'farm_state.json'

# Глобальные переменные состояния
bot_states = {bot: 'IDLE' for bot in TARGET_BOTS}
transfer_amounts = {bot: 0.0 for bot in TARGET_BOTS}
bot_intervals = {bot: 1200 for bot in TARGET_BOTS}
my_user_id = None

# Создание клиента с учетом прокси
if PROXY_ENABLED and PROXY_SERVER and PROXY_PORT and PROXY_SECRET:
    print(f"🔐 Подключаюсь через MTProto прокси: {PROXY_SERVER}:{PROXY_PORT}")
    client = TelegramClient(
        SESSION_NAME, API_ID, API_HASH,
        connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
        proxy=(PROXY_SERVER, PROXY_PORT, PROXY_SECRET)
    )
else:
    print("🔓 Подключаюсь напрямую (без прокси)")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


def load_state():
    global bot_states
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                saved_states = json.load(f)
                for bot in TARGET_BOTS:
                    if bot in saved_states:
                        bot_states[bot] = saved_states[bot]
            print("📁 Состояния загружены из файла:", bot_states)
        except Exception as e:
            print(f"❌ Ошибка чтения state-файла: {e}")


def save_state():
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(bot_states, f)
    except Exception as e:
        pass


async def estimate_bot_interval(bot_name):
    """Высчитывает время между сообщениями 'пропала' и 'вернулась' за последнее время"""
    try:
        messages = await client.get_messages(bot_name, limit=40)
        intervals = []

        # Сообщения идут от новых к старым (index 0 = самое новое)
        for i in range(len(messages) - 1):
            if "Ссылка вернулась" in (messages[i].text or ""):
                for j in range(i + 1, len(messages)):
                    if "пропала из твоего профиля!" in (messages[j].text or ""):
                        # Считаем разницу во времени
                        diff = messages[i].date.timestamp() - messages[j].date.timestamp()
                        # Разумные ограничения: от 5 минут до 60 минут
                        if 300 <= diff <= 3600:
                            intervals.append(diff)
                        break  # Нашли пару, идем дальше

        if intervals:
            # Берем среднее значение последних удачных интервалов
            avg_interval = sum(intervals[:3]) / len(intervals[:3])
            print(f"⏱ [{bot_name}]: Вычислен интервал проверки бота: ~{int(avg_interval // 60)} мин.")
            return avg_interval

    except Exception as e:
        print(f"❌ Ошибка вычисления интервала для {bot_name}: {e}")

    print(f"⏱ [{bot_name}]: Мало свежих данных. Ставлю интервал по умолчанию (20 мин).")
    return 1200  # 20 минут по умолчанию


async def sync_states_from_history():
    print("🔍 Проверяю историю переписки и считаю тайминги...")
    for bot in TARGET_BOTS:
        # 1. Высчитываем тайминги бота
        bot_intervals[bot] = await estimate_bot_interval(bot)

        # 2. Восстанавливаем статус
        try:
            messages = await client.get_messages(bot, limit=3)
            for msg in messages:
                if not msg.text: continue
                if "пропала из твоего профиля!" in msg.text:
                    bot_states[bot] = 'WAITING'
                    break
                elif "Ссылка вернулась" in msg.text:
                    bot_states[bot] = 'TRANSFERRING'
                    await client.send_message(bot, "Профиль")
                    break
                elif "Мой Профиль" in msg.text or "Успех!" in msg.text:
                    if bot_states[bot] != 'TRANSFERRING':
                        bot_states[bot] = 'IDLE'
                    break
        except Exception as e:
            print(f"❌ Не смог прочитать историю {bot}: {e}")

    save_state()


async def send_notification(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": GROUP_ID, "text": text, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except:
        pass


def parse_balance(text):
    try:
        start = text.find("Обычный:")
        if start == -1: return 0.0
        match = re.search(r"[\d.]+", text[start + len("Обычный:"):])
        if match: return float(match.group(0))
    except:
        pass
    return 0.0


# --- УМНЫЙ РОТАТОР ---

async def bio_rotator():
    current_bio_bot = None
    last_swap_time = 0

    while True:
        try:
            waiting_bots = [bot for bot, state in bot_states.items() if state == 'WAITING']

            if not waiting_bots:
                if current_bio_bot is not None:
                    print("🧹 Все ссылки найдены. Возвращаю чистое био...")
                    await client(UpdateProfileRequest(about=CLEAN_BIO))
                    current_bio_bot = None

            elif len(waiting_bots) == 1:
                target = waiting_bots[0]
                if current_bio_bot != target:
                    link = f"https://t.me/{target}?start=ref_{my_user_id}"
                    print(f"✏️ В био установлена ссылка для: {target}")
                    await client(UpdateProfileRequest(about=link))
                    current_bio_bot = target

            else:
                # Если ждут ОБА бота, используем логику "Капкана"
                now = time.time()

                # Сколько держать ссылку текущего бота?
                # Берём его высчитанный интервал + 3 минуты сверху для надежности (180 сек)
                hold_time = bot_intervals.get(current_bio_bot, 1200) + 180

                # Если время вышло ИЛИ в био стоит вообще чужой бот
                if now - last_swap_time > hold_time or current_bio_bot not in waiting_bots:
                    # Выбираем следующего бота
                    next_bot = waiting_bots[0] if current_bio_bot != waiting_bots[0] else waiting_bots[1]
                    link = f"https://t.me/{next_bot}?start=ref_{my_user_id}"

                    next_hold_mins = int((bot_intervals.get(next_bot, 1200) + 180) // 60)
                    print(f"🔄 Ротация: Ставлю {next_bot}. Капкан взведен на {next_hold_mins} минут.")

                    await client(UpdateProfileRequest(about=link))
                    current_bio_bot = next_bot
                    last_swap_time = time.time()

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            pass

        await asyncio.sleep(10)


# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@client.on(events.NewMessage(chats=TARGET_BOTS))
async def handle_bot_messages(event):
    chat = await event.get_chat()
    bot_name = chat.username
    text = event.message.text

    if "пропала из твоего профиля!" in text:
        print(f"🤖 [{bot_name}]: Обнаружил пропажу ссылки.")
        bot_states[bot_name] = 'WAITING'
        save_state()

    elif "Ссылка вернулась" in text:
        print(f"🤖 [{bot_name}]: Бонус восстановлен.")
        bot_states[bot_name] = 'TRANSFERRING'
        save_state()

        # Пересчитываем интервал после успешного цикла, чтобы адаптироваться к изменениям
        bot_intervals[bot_name] = await estimate_bot_interval(bot_name)

        delay = random.randint(10, 20)
        await asyncio.sleep(delay)
        await event.respond("Профиль")

    elif "Мой Профиль" in text and "Баланс" in text:
        balance = parse_balance(text)
        if balance <= 0.01:
            bot_states[bot_name] = 'IDLE'
            save_state()
            return

        transfer_amounts[bot_name] = round(balance, 2)
        buttons = await event.message.get_buttons()
        for row in buttons:
            for button in row:
                if button.data and button.data.decode('utf-8') == 'transfer.stars':
                    await asyncio.sleep(random.randint(3, 7))
                    await button.click()
                    return

    elif "Перевод баланса" in text and "Введи получателя и" in text:
        amount = transfer_amounts.get(bot_name, 0.0)
        if amount > 0:
            transfer_msg = f"{RECIPIENT} {amount}"
            await asyncio.sleep(random.randint(5, 12))
            await event.respond(transfer_msg)

    elif "с учетом 5% комиссии" in text and "Получатель получит" in text:
        buttons = await event.message.get_buttons()
        for row in buttons:
            for button in row:
                if button.data and button.data.decode('utf-8') == 'transfer.confirm':
                    await asyncio.sleep(random.randint(4, 8))
                    await button.click()
                    return


    elif "Успех!" in text and "комиссия: 5%" in text:

        stars_match = re.search(r"(\d+(?:\.\d+)?)\s*⭐", text)

        stars_amount = stars_match.group(1) if stars_match else transfer_amounts.get(bot_name, "?")

        # Парсим комиссию и итоговую сумму

        commission_match = re.search(r"комиссия:\s*([\d.]+)\s*⭐", text)

        total_match = re.search(r"Итого:\s*([\d.]+)\s*⭐", text)

        commission = commission_match.group(1) if commission_match else "?"

        total_amount = total_match.group(1) if total_match else stars_amount

        # Красивое оформление

        notification_text = (

            f"💰 <b>Успешный перевод!</b>\n"

            f"├─ От: <code>@{bot_name}</code>\n"

            f"├─ Кому: {RECIPIENT}\n"

            f"├─ Сумма: <b>{stars_amount} ⭐</b>\n"

            f"├─ Комиссия: {commission} ⭐\n"

            f"└─ Итого получено: <b>{total_amount} ⭐</b>\n\n"

            f"✅ <i>Цикл для @{bot_name} завершён</i>"

        )

        await send_notification(notification_text)

        bot_states[bot_name] = 'IDLE'

        transfer_amounts[bot_name] = 0.0

        save_state()

        print(f"🎯 Цикл для {bot_name} завершен. Переведено: {stars_amount} ⭐")


async def main():
    global my_user_id
    await client.start()

    me = await client.get_me()
    my_user_id = me.id

    load_state()
    await sync_states_from_history()

    print(f"🚀 Юзербот запущен. ID: {my_user_id}")
    client.loop.create_task(bio_rotator())
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())

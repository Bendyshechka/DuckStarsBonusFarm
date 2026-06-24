#!/usr/bin/env python3
import json
import os
import sys
import re

CONFIG_FILE = "config.json"

BANNER = """
╔══════════════════════════════════════════════╗
║          🦆 DUCK FARM CONFIG SETUP           ║
╚══════════════════════════════════════════════╝
"""


def color_text(text, color_code):
    """Добавляет ANSI-цвета, если терминал поддерживает."""
    if os.name == 'nt':  # Windows
        return text
    return f"\033[{color_code}m{text}\033[0m"


def green(text): return color_text(text, "92")


def yellow(text): return color_text(text, "93")


def cyan(text): return color_text(text, "96")


def red(text): return color_text(text, "91")


def bold(text): return color_text(text, "1")


def magenta(text): return color_text(text, "95")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def load_config():
    """Загружает существующий конфиг, если есть."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Обеспечиваем наличие секции proxy
                if 'proxy' not in config:
                    config['proxy'] = {
                        "enabled": False,
                        "server": "",
                        "port": 0,
                        "secret": ""
                    }
                return config
        except:
            pass
    return {
        'proxy': {
            "enabled": False,
            "server": "",
            "port": 0,
            "secret": ""
        }
    }


def save_config(config):
    """Сохраняет конфиг в файл."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(green("\n✅ Конфигурация успешно сохранена в config.json"))


def validate_input(value, field_name):
    """Базовая валидация полей."""
    if not value or not value.strip():
        print(red(f"❌ Поле '{field_name}' не может быть пустым!"))
        return False

    if field_name == "API ID":
        try:
            int(value)
        except ValueError:
            print(red("❌ API ID должен быть числом!"))
            return False

    if field_name == "Порт прокси":
        try:
            port = int(value)
            if port < 1 or port > 65535:
                print(red("❌ Порт должен быть от 1 до 65535!"))
                return False
        except ValueError:
            print(red("❌ Порт должен быть числом!"))
            return False

    if field_name == "Секретный ключ" and not re.match(r'^[a-fA-F0-9]{32}$', value):
        print(yellow("⚠️ Секретный ключ обычно состоит из 32 hex-символов. Продолжить? (Enter - да, n - нет)"))
        if input("> ").lower() == 'n':
            return False

    if field_name == "Сервер прокси" and not re.match(r'^[\d.]+$', value):
        print(yellow("⚠️ Похоже, это не IP-адрес. Продолжить? (Enter - да, n - нет)"))
        if input("> ").lower() == 'n':
            return False

    if field_name in ["Получатель", "Группа (GROUP_ID)"] and not value.startswith(
            "@" if field_name == "Получатель" else "-"):
        if field_name == "Получатель":
            print(yellow("⚠️ Получатель обычно начинается с @. Продолжить? (Enter - да, n - нет)"))
        else:
            print(yellow("⚠️ ID группы обычно начинается с -100. Продолжить? (Enter - да, n - нет)"))
        if input("> ").lower() == 'n':
            return False

    return True


def proxy_menu(config):
    """Меню настройки прокси."""
    while True:
        clear_screen()
        print(BANNER)
        print(magenta("🔐 НАСТРОЙКА MTProto ПРОКСИ"))
        print("─" * 46)

        proxy = config['proxy']
        enabled = proxy.get('enabled', False)

        status_color = green if enabled else red
        status_text = "ВКЛЮЧЕН" if enabled else "ВЫКЛЮЧЕН"

        print(f"  Статус прокси: {status_color(bold(status_text))}")
        print("─" * 46)

        if enabled:
            print(f"  1. Сервер:    {cyan(proxy.get('server', 'Не задан') or 'Не задан')}")
            print(f"  2. Порт:      {cyan(str(proxy.get('port', 'Не задан')))}")
            print(
                f"  3. Secret:    {cyan(proxy.get('secret', 'Не задан')[:8] + '...' if proxy.get('secret') else 'Не задан')}")
        else:
            print(f"  1. Сервер:    {red('Прокси выключен')}")
            print(f"  2. Порт:      {red('Прокси выключен')}")
            print(f"  3. Secret:    {red('Прокси выключен')}")

        print("─" * 46)
        print(f"\n  4. {bold('Переключить прокси (Вкл/Выкл)')}")
        print(f"  5. {green('Назад в главное меню')}")

        choice = input(f"\n{cyan('Выберите пункт (1-5):')} ").strip()

        if choice == '4':
            proxy['enabled'] = not enabled
            status = "включен" if proxy['enabled'] else "выключен"
            print(green(f"✅ Прокси {status}!"))
            input("\nНажмите Enter...")
        elif choice == '5':
            return
        elif choice in ['1', '2', '3'] and not enabled:
            print(red("❌ Сначала включите прокси (пункт 4)!"))
            input("\nНажмите Enter...")
        elif choice == '1' and enabled:
            edit_proxy_field(config, 'server', 'Сервер прокси', 'Введите IP-адрес прокси (например: 127.0.0.1)')
        elif choice == '2' and enabled:
            edit_proxy_field(config, 'port', 'Порт прокси', 'Введите порт (например: 1443)')
        elif choice == '3' and enabled:
            edit_proxy_field(config, 'secret', 'Секретный ключ', 'Введите секретный ключ (32 hex-символа)')
        else:
            print(red("Неверный выбор!"))
            input("\nНажмите Enter...")


def edit_proxy_field(config, key, name, prompt):
    """Редактирует конкретное поле прокси."""
    clear_screen()
    print(BANNER)
    print(cyan(f"✏️ Редактирование: {name}"))
    print("─" * 46)

    current = config['proxy'].get(key)
    if current:
        display = current
        if key == 'secret':
            display = current[:8] + '...' if len(str(current)) > 8 else current
        print(yellow(f"Текущее значение: {display}"))

    new_value = input(f"\n{prompt}\n{'> ' if not current else '(Enter оставить текущее) > '}").strip()

    if not new_value and current:
        print(green("✅ Оставлено текущее значение."))
    elif validate_input(new_value, name):
        if key == 'port':
            config['proxy'][key] = int(new_value)
        else:
            config['proxy'][key] = new_value
        print(green(f"✅ {name} обновлен!"))
    else:
        print(red("Изменения не применены."))

    input("\nНажмите Enter для возврата...")


def main_menu(config):
    """Отображает главное меню настроек."""
    while True:
        clear_screen()
        print(BANNER)
        print(cyan("📋 Текущая конфигурация:"))
        print("─" * 46)

        proxy_enabled = config.get('proxy', {}).get('enabled', False)
        proxy_status = green("🔒 ВКЛ") if proxy_enabled else red("🔓 ВЫКЛ")

        fields_display = {
            "API ID": config.get('api_id', '❌ Не задано'),
            "API HASH": ('✅ Задан' if config.get('api_hash') else '❌ Не задан'),
            "Получатель (RECIPIENT)": config.get('recipient', '❌ Не задан'),
            "Токен бота (BOT_TOKEN)": ('✅ Задан' if config.get('bot_token') else '❌ Не задан'),
            "Группа (GROUP_ID)": config.get('group_id', '❌ Не задан'),
            "Прокси (MTProto)": proxy_status
        }

        for i, (key, value) in enumerate(fields_display.items(), 1):
            status_color = green if ('✅' in str(value) or 'ВКЛ' in str(value)) and '❌' not in str(value) else red
            print(f"  {i}. {key}: {status_color(str(value))}")

        print("─" * 46)
        print(f"\n  {magenta('7.')} {bold('⚙️ Настроить прокси')}")
        print(f"  {yellow('8.')} {bold('Сохранить и выйти')}")
        print(f"  {red('9.')} Выйти без сохранения")

        if len([v for v in [config.get('api_id'), config.get('api_hash'),
                            config.get('recipient'), config.get('bot_token'),
                            config.get('group_id')] if v]) == 5:
            print(green("\n✅ Все основные поля заполнены!"))

        choice = input(f"\n{cyan('Выберите пункт (1-9):')} ").strip()

        if choice == '1':
            edit_field(config, 'api_id', 'API ID', 'Введите API ID (число)')
        elif choice == '2':
            edit_field(config, 'api_hash', 'API HASH', 'Введите API HASH')
        elif choice == '3':
            edit_field(config, 'recipient', 'Получатель (RECIPIENT)', 'Введите получателя (например: @username)')
        elif choice == '4':
            edit_field(config, 'bot_token', 'Токен бота (BOT_TOKEN)', 'Введите токен бота (формат: 123:ABC...)')
        elif choice == '5':
            edit_field(config, 'group_id', 'Группа (GROUP_ID)', 'Введите ID группы (например: -100123456789)')
        elif choice == '7':
            proxy_menu(config)
        elif choice == '8':
            # Проверка заполненности основных полей
            empty_fields = [name for key, name in [
                ('api_id', 'API ID'),
                ('api_hash', 'API HASH'),
                ('recipient', 'Получатель'),
                ('bot_token', 'Токен бота'),
                ('group_id', 'ID группы')
            ] if not config.get(key)]

            if empty_fields:
                print(red(f"\n❌ Не заполнены поля: {', '.join(empty_fields)}"))
                print(yellow("Заполните все поля перед сохранением."))
                input("\nНажмите Enter для продолжения...")
                continue

            # Проверка прокси если включен
            if config.get('proxy', {}).get('enabled', False):
                proxy = config['proxy']
                proxy_empty = []
                if not proxy.get('server'): proxy_empty.append('сервер')
                if not proxy.get('port'): proxy_empty.append('порт')
                if not proxy.get('secret'): proxy_empty.append('секретный ключ')

                if proxy_empty:
                    print(red(f"\n❌ Прокси включен, но не заполнены: {', '.join(proxy_empty)}"))
                    print(yellow("Заполните все поля прокси или выключите его."))
                    input("\nНажмите Enter для продолжения...")
                    continue

            save_config(config)
            return True
        elif choice == '9':
            print(yellow("\n👋 Выход без сохранения."))
            return False
        else:
            print(red("Неверный выбор. Попробуйте снова."))
            input("\nНажмите Enter...")


def edit_field(config, key, name, prompt):
    """Редактирует конкретное поле."""
    clear_screen()
    print(BANNER)
    print(cyan(f"✏️ Редактирование: {name}"))
    print("─" * 46)

    current = config.get(key)
    if current:
        print(yellow(f"Текущее значение: {current}"))

    if key == 'api_hash':
        print(yellow("(Вводится скрыто для безопасности)"))

    new_value = input(f"\n{prompt}\n{'> ' if not current else '(Enter оставить текущее) > '}").strip()

    if not new_value and current:
        print(green("✅ Оставлено текущее значение."))
    elif validate_input(new_value, name):
        if key == 'api_id':
            config[key] = int(new_value)
        else:
            config[key] = new_value
        print(green(f"✅ {name} обновлен!"))
    else:
        print(red("Изменения не применены."))

    input("\nНажмите Enter для возврата в меню...")


def first_time_setup():
    """Настройка с нуля (пошаговый режим)."""
    config = load_config()

    clear_screen()
    print(BANNER)
    print(cyan("🚀 Первичная настройка конфигурации\n"))
    print("Следуйте инструкциям для заполнения всех полей.\n")
    print("─" * 46)

    # API ID
    while True:
        api_id = input("\n1/5. Введите API ID: ").strip()
        if validate_input(api_id, "API ID"):
            config['api_id'] = int(api_id)
            break

    # API HASH
    while True:
        api_hash = input("2/5. Введите API HASH: ").strip()
        if validate_input(api_hash, "API HASH"):
            config['api_hash'] = api_hash
            break

    # Recipient
    while True:
        recipient = input("3/5. Введите получателя (RECIPIENT): ").strip()
        if validate_input(recipient, "Получатель"):
            config['recipient'] = recipient
            break

    # Bot Token
    while True:
        bot_token = input("4/5. Введите токен бота (BOT_TOKEN): ").strip()
        if validate_input(bot_token, "Токен бота"):
            config['bot_token'] = bot_token
            break

    # Group ID
    while True:
        group_id = input("5/5. Введите ID группы (GROUP_ID): ").strip()
        if validate_input(group_id, "Группа"):
            config['group_id'] = group_id
            break

    print("\n" + "─" * 46)

    # Спрашиваем про прокси
    use_proxy = input(yellow("\n🔐 Использовать MTProto прокси? (y/n): ")).lower()
    if use_proxy == 'y':
        config['proxy']['enabled'] = True

        print(cyan("\nНастройка прокси:"))
        while True:
            server = input("Сервер (IP): ").strip()
            if validate_input(server, "Сервер прокси"):
                config['proxy']['server'] = server
                break

        while True:
            port = input("Порт: ").strip()
            if validate_input(port, "Порт прокси"):
                config['proxy']['port'] = int(port)
                break

        while True:
            secret = input("Секретный ключ (32 hex): ").strip()
            if validate_input(secret, "Секретный ключ"):
                config['proxy']['secret'] = secret
                break

    print("\n" + "─" * 46)
    print(green("\n✅ Все поля заполнены!"))
    save_config(config)

    return config


def main():
    """Точка входа."""
    config = load_config()

    if any([config.get('api_id'), config.get('api_hash'), config.get('recipient'),
            config.get('bot_token'), config.get('group_id')]):
        # Есть частично заполненный конфиг - показываем меню
        main_menu(config)
    else:
        # Полностью пустой конфиг - пошаговая настройка
        first_time_setup()

    print(green("\n✨ Готово! Можно запускать основной скрипт."))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(red("\n\n❌ Настройка прервана пользователем."))
        sys.exit(0)

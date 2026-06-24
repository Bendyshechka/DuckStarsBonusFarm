#!/usr/bin/env python3
import json
import os
import sys

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


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def load_config():
    """Загружает существующий конфиг, если есть."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


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

    if field_name in ["Получатель", "Группа (GROUP_ID)"] and not value.startswith(
            "@" if field_name == "Получатель" else "-"):
        if field_name == "Получатель":
            print(yellow("⚠️ Получатель обычно начинается с @. Продолжить? (Enter - да, n - нет)"))
        else:
            print(yellow("⚠️ ID группы обычно начинается с -100. Продолжить? (Enter - да, n - нет)"))
        if input("> ").lower() == 'n':
            return False

    return True


def main_menu(config):
    """Отображает главное меню настроек."""
    while True:
        clear_screen()
        print(BANNER)
        print(cyan("📋 Текущая конфигурация:"))
        print("─" * 46)

        fields_display = {
            "API ID": config.get('api_id', '❌ Не задано'),
            "API HASH": ('✅ Задан' if config.get('api_hash') else '❌ Не задан'),
            "Получатель (RECIPIENT)": config.get('recipient', '❌ Не задан'),
            "Токен бота (BOT_TOKEN)": ('✅ Задан' if config.get('bot_token') else '❌ Не задан'),
            "Группа (GROUP_ID)": config.get('group_id', '❌ Не задан')
        }

        for i, (key, value) in enumerate(fields_display.items(), 1):
            status_color = green if '✅' in str(value) or value != '❌ Не задан' and '❌' not in str(value) else red
            print(f"  {i}. {key}: {status_color(str(value))}")

        print("─" * 46)
        print(f"\n  {yellow('6.')} {bold('Сохранить и выйти')}")
        print(f"  {red('7.')} Выйти без сохранения")

        if len([v for v in config.values() if v and str(v).strip()]) == 5:
            print(green("\n✅ Все поля заполнены! Можно сохранять."))

        choice = input(f"\n{cyan('Выберите пункт (1-7):')} ").strip()

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
        elif choice == '6':
            # Проверка заполненности
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

            save_config(config)
            return True
        elif choice == '7':
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
    config = {}

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
    print(green("\n✅ Все поля заполнены!"))
    save_config(config)

    return config


def main():
    """Точка входа."""
    config = load_config()

    if config:
        # Есть существующий конфиг - показываем меню
        main_menu(config)
    else:
        # Конфига нет - пошаговая настройка
        if not os.path.exists(CONFIG_FILE):
            print(yellow("📝 Конфигурационный файл не найден. Запускаю первичную настройку..."))
        first_time_setup()

    print(green("\n✨ Готово! Можно запускать основной скрипт."))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(red("\n\n❌ Настройка прервана пользователем."))
        sys.exit(0)
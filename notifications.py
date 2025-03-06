import asyncio
import os
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
import schedule

import database_functions as dbf

# Настройки
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
logging.basicConfig(level=logging.INFO)

global GLOBAL_COUNTER
GLOBAL_COUNTER = 0

async def split_text(text, max_length=4096):
    parts = text.split(',')  
    result, current_part = [], ''
    for part in parts:
        if len(current_part) + len(part) + 1 <= max_length:
            current_part += (',' if current_part else '') + part
        else:
            result.append(current_part)
            current_part = part
    if current_part:
        result.append(current_part)
    return result

async def start_sending_notifications() -> None:
    global GLOBAL_COUNTER
    
    list_today_birthdays = dbf.list_birthdays_all(days_delta=0)
    list_tomorrow_birthdays = dbf.list_birthdays_all(days_delta=1)
    list_inaweek_birthdays = dbf.list_birthdays_all(days_delta=7)

    birthdays = [
        {'answer': 'Сегодня день рождения у ', 'birthdays': list_today_birthdays}, 
        {'answer': 'Завтра день рождения у ', 'birthdays': list_tomorrow_birthdays}, 
        {'answer': 'Через неделю день рождения у ', 'birthdays': list_inaweek_birthdays}
        ]

    for entity in birthdays:
        list_birthdays_local = entity['birthdays']
        answer = entity['answer']
        i = 0
        while i < len(list_birthdays_local):
            item = list_birthdays_local[i]
            try:
                answer += item['name']
                if len(answer) > 4096:
                    answers = await split_text(answer)
                    for loc_answer in range(len(answers) - 1):
                        await bot.send_message(item['user_id'], answers[loc_answer])
                    await bot.send_message(item['user_id'], answers[-1] + '! 🎉')
                else:
                    await bot.send_message(item['user_id'], answer + '! 🎉')
                GLOBAL_COUNTER += 1
            except TelegramRetryAfter as e:
                logging.warning(f"Возникла ошибка RetryAfter. Спим {e.retry_after} секунд...")
                await asyncio.sleep(e.retry_after + 0.5)
                i += -1  # Возврат к данной итерации
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение пользователю {item['user_id']}. Ошибка: {e}")
            if i % 3:
                await asyncio.sleep(0.2)
            i += 1

    return 0
            

async def main():
    logging.info("Рассылка уведомлений запущена.")
    await start_sending_notifications()
    logging.info(f"Рассылка уведомлений окончена. Отправлено уведомлений: {GLOBAL_COUNTER}")

async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)

if __name__ == "__main__":
    logging.info('Демон запущен.')
    schedule.every().day.at("08:00").do(lambda: asyncio.create_task(main()))
    asyncio.run(run_scheduler())

import os
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import CallbackQuery
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

import database_functions as dbf
import keyboards as kb

# Настройки
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# FSM
class AddBirthday(StatesGroup):
    name = State()
    birthday = State()
    notify = State()

async def split_text(text: str, max_length: int = 4096) -> list:
    lines = text.split('\n')
    result, current_line = [], ''
    for line in lines:
        if len(current_line) + len(line) + 1 <= max_length:
            current_line += ('\n' if current_line else '') + line
        else:
            result.append(current_line)
            current_line = line
    if current_line:
        result.append(current_line)
    return result

@dp.message(Command("start"))
async def start(message: types.Message) -> None:
    await message.answer("Привет! Я бот для напоминания о днях рождения!\n\nТы можешь добавить дни рождения, и выбранное количество "\
                         "дней тебе будет приходить уведомление 🥳", reply_markup=kb.main_keyboard)

@dp.message(Command("main"))
async def start(message: types.Message) -> None:
    await message.answer("Ты можешь добавить дни рождения, посмотреть список или изменить их - для этого выбери необходимую кнопку "\
                         "в нижней части экрана😉", reply_markup=kb.main_keyboard)

@dp.message(F.text == "Добавить дни рождения 🪄")
async def add_birthday_start(message: types.Message, state: FSMContext) -> None:
    await state.set_state(AddBirthday.name)
    await message.answer("Введи имя того, о чьём ДР хочешь получать напоминания:", reply_markup=kb.cancel_keyboard)
    await state.update_data(user_id=message.from_user.id)

@dp.message(AddBirthday.name)
async def add_birthday_name(message: types.Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(AddBirthday.birthday)
    await message.answer("Введи дату рождения в формате ДД.ММ.ГГГГ или ДД.ММ:", reply_markup=kb.cancel_keyboard)

@dp.message(AddBirthday.birthday)
async def add_birthday_date(message: types.Message, state: FSMContext) -> None:
    date_text = message.text
    if re.fullmatch(r"\d{2}\.\d{2}", date_text):  # ДД.ММ
        date_text += ".1900"
        await state.update_data(store_year=False)
    elif re.fullmatch(r"\d{2}\.\d{2}.\d{4}", date_text):  # ДД.ММ.ГГГГ:
        await state.update_data(store_year=True)
    else:
        await message.answer("Ошибка! \nДата введена в неверном формате.\n\nВведи дату рождения в формате ДД.ММ.ГГГГ или ДД.ММ, "\
                             "например 01.01.1990", 
                             reply_markup=kb.cancel_keyboard)
        return None
    
    birthday = datetime.strptime(date_text, "%d.%m.%Y").date()
    await state.update_data(birthday=birthday)
    await state.set_state(AddBirthday.notify)
    await state.update_data(notify_before_week=True)
    await state.update_data(notify_before_day=True)
    await state.update_data(notify_in_today=True)
    data = await state.get_data()
    await message.answer("Выбери время напоминаний:", reply_markup=kb.choose_correct_notify_keyboard(data))

async def update_notification_state(state: FSMContext, callback: CallbackQuery, key, value) -> None:
    await state.update_data(**{key: value})
    data = await state.get_data()
    keyboard = kb.choose_correct_notify_keyboard(data)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

@dp.callback_query(AddBirthday.notify, F.data.startswith("notify_set_"))
async def add_birthday_notify(callback: CallbackQuery, state: FSMContext) -> None:
    callback_data = callback.data.split('_')
    notify_keys = {
        'before-week': 'notify_before_week',
        'before-day': 'notify_before_day',
        'today': 'notify_in_today'
    }
    
    notify_type = callback_data[3]
    notify_value = callback_data[2]
    
    if notify_type in notify_keys:
        if notify_value in {'0', '1'}:
            await update_notification_state(state, callback, notify_keys[notify_type], notify_value == '1')
        else:
            logging.error(f"Произошла ошибка: неизвестный callback. callback_data:{callback_data}, user_id={callback.from_user.id}.")
            await callback.message.answer("Произошла ошибка. Попробуйте позже.")
            await state.clear()
    else:
        logging.error(f"Произошла ошибка: неизвестный callback. callback_data:{callback_data}, user_id={callback.from_user.id}.")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()    

@dp.callback_query(AddBirthday.notify, F.data == ("approve_adding"))
async def add_birthday_notify(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()    
    adding = dbf.add_birthday(**data)
    if adding:
        await callback.message.edit_text(f"День рождения успешно добавлен! 🎂\n\nИмя: {data['name']}\n" \
                                      f"День рождения: {datetime.strftime(data['birthday'], "%d.%m.%Y") if data['store_year'] else datetime.strftime(data['birthday'], "%d.%m")}\n\n" \
                                      f"{'Напоминание:\n' }"\
                                      f"{'✅ за неделю\n' if data['notify_before_week'] else '❌ за неделю\n'}"\
                                      f"{'✅ за день\n' if data['notify_before_day'] else '❌ за день\n'}"\
                                      f"{'✅ в ДР\n' if data['notify_in_today'] else '❌ за день\n'}"
                                      )
        logging.info(f"Пользователь {data["user_id"]} добавил ДР: {data}")
    else:
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
    await state.clear()

async def get_birthdays(user_id: int, current_month: int, return_str: bool = True) -> str|list:
    months = ["январе", "феврале", "марте", "апреле", "мае", "июне", "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"]
    answer = f'Список{" всех" if current_month == 0 else ""} дней рождения{" в " + months[(current_month - 1) % 12] if current_month > 0 else ""}:\n'
    list_birthdays_local = []
    result = dbf.list_birthdays(user_id, month=current_month)
    for i, entity in enumerate(result):
        birthday = f"{datetime.strftime(entity['birthday'], "%d.%m.%Y") if entity['store_year'] else datetime.strftime(entity['birthday'], "%d.%m")}"
        if return_str:
            answer += f"\n{i+1}. {entity['name']}, ДР: {birthday}"
        else:
            list_birthdays_local.append({'id': entity['id'], 'name': f"{i+1}. {entity['name']}"})
    if return_str:
        return answer
    else:
        return list_birthdays_local

@dp.message(F.text == "Список дней рождения 👀")
async def list_birthdays_current(message: types.Message) -> None:
    current_month = datetime.now().month
    answer = await get_birthdays(message.from_user.id, current_month)
    if len(answer) > 4096:
        answers = await split_text(answer)
        for loc_answer in range(len(answers) - 1):
            await message.answer(loc_answer)
        await message.answer(answers[-1], reply_markup=kb.get_month_keyboard(current_month))
    else:
        await message.answer(answer, reply_markup=kb.get_month_keyboard(current_month))

@dp.callback_query(F.data.startswith("list_select_month_"))
async def list_birthdays(callback: CallbackQuery) -> None:
    callback_data = callback.data.split('_')
    current_month = int(datetime.now().month)
    match callback_data[-1]:
        case "all":
            answer = await get_birthdays(callback.from_user.id, 0)
            if len(answer) > 4096:
                answers = await split_text(answer)
                for loc_answer in range(len(answers) - 1):
                    await callback.message.answer(answers[loc_answer])
                await callback.message.answer(answers[-1], reply_markup=kb.get_month_keyboard(current_month))
            else:
                await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(current_month))
        case "none":
            ...
        case "list":
            answer = 'Выбери месяц:'
            await callback.message.edit_text(answer, reply_markup=kb.list_months)
        case "update":
            answer = 'Выбери запись, которую необходимо удалить:'
            birthdays_local = await get_birthdays(callback.from_user.id, int(callback_data[-2]), False)
            show_choose_buttons = False
            if len(birthdays_local) > 20:
                show_choose_buttons = True
            keyboard = kb.get_entries_list(birthdays_local, callback_data[-2], show_choose_buttons, 0)
            await callback.message.edit_text(answer, reply_markup=keyboard)
        case _:
            if callback_data[-1].isdigit() and 1 <= int(callback_data[-1]) <= 12:
                answer = await get_birthdays(callback.from_user.id, int(callback_data[-1]))
                if len(answer) > 4096:
                    answers = await split_text(answer)
                    for loc_answer in range(len(answers) - 1):
                        await callback.message.answer(answers[loc_answer])
                    await callback.message.answer(answers[-1], reply_markup=kb.get_month_keyboard(int(callback_data[-1])))
                else:
                    await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(int(callback_data[-1])))
            else:
                answer = 'Произошла ошибка при выборе месяца.\n\n'
                answer += await get_birthdays(callback.from_user.id, current_month)
                if len(answer) > 4096:
                    answers = await split_text(answer)
                    for loc_answer in range(len(answers) - 1):
                        await callback.message.answer(answers[loc_answer])
                    await callback.message.answer(answers[-1], reply_markup=kb.get_month_keyboard(current_month))
                else:
                    await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(current_month))

@dp.callback_query(F.data.startswith("del_"))
async def edit_entries(callback: CallbackQuery) -> None:
    callback_data = callback.data.split('_')
    match callback_data[-1]:
        case "right":
            month = int(callback_data[1].split('=')[-1])
            answer = 'Выбери запись, которую необходимо удалить:'
            birthdays_local = await get_birthdays(callback.from_user.id, month, False)
            show_choose_buttons = False
            if len(birthdays_local) > 20:
                show_choose_buttons = True
            keyboard = kb.get_entries_list(birthdays_local, month, show_choose_buttons, int(callback_data[-2]))
            await callback.message.edit_text(answer, reply_markup=keyboard)
        case "left":
            month = int(callback_data[1].split('=')[-1])
            answer = 'Выбери запись, которую необходимо удалить:'
            birthdays_local = await get_birthdays(callback.from_user.id, month, False)
            show_choose_buttons = False
            if len(birthdays_local) > 20:
                show_choose_buttons = True
            keyboard = kb.get_entries_list(birthdays_local, month, show_choose_buttons, int(callback_data[-2]))
            await callback.message.edit_text(answer, reply_markup=keyboard)
        case "none":
           ...
        case "tolist":
            month = int(callback_data[1].split('=')[-1])
            answer = await get_birthdays(callback.from_user.id, month)
            if len(answer) > 4096:
                answers = await split_text(answer)
                for loc_answer in range(len(answers) - 1):
                    await callback.message.answer(answers[loc_answer])
                await callback.message.answer(answers[-1], reply_markup=kb.get_month_keyboard(month))
            else:
                await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(month))
        case _:
            if callback_data[-1].isdigit():
                month = int(callback_data[1].split('=')[-1])
                result = dbf.del_birthday(callback.from_user.id, int(callback_data[-1]))
                if result:
                    answer = 'Запись удалена.\n'
                else:
                    answer = 'Произошла ошибка при удалении записи.'
                answer += await get_birthdays(callback.from_user.id, month)
                await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(month))
            else:
                current_month = datetime.now().month
                answer = 'Произошла ошибка. \n'
                answer += await get_birthdays(callback.from_user.id, current_month)
                await callback.message.edit_text(answer, reply_markup=kb.get_month_keyboard(current_month))


@dp.callback_query(F.data == ("cancel_states"))
async def cancel_now_state(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return None
    else:
        await state.clear()
        await callback.message.answer(f"Действие отменено.")

@dp.message()
async def text_not_defined(message: types.Message) -> None:
    answer = f'Я тебя не понял.\n\nТы можешь добавить дни рождения, посмотреть список или изменить их - для этого выбери необходимую кнопку в нижней части экрана😉'
    await message.answer(answer, reply_markup=kb.main_keyboard)

async def main():
    logging.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

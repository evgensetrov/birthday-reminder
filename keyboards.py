from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton

# Основная клавиатура
main_keyboard = ReplyKeyboardBuilder()
main_keyboard.row(KeyboardButton(text="Добавить дни рождения 🪄"))
main_keyboard.row(KeyboardButton(text="Список дней рождения 👀"))
main_keyboard = main_keyboard.as_markup(resize_keyboard=True)

# Клавиатура выбора дат уведомлений
def create_notify_keyboard(state: str) -> InlineKeyboardBuilder:
    """
    Создает клавиатуру на основе состояния (трёхбитная строка, например '101').
    """
    labels = ["За 7 дней", "За день", "В день"]
    callback_prefix = ["before-week", "before-day", "today"]
    
    keyboard = InlineKeyboardBuilder()
    
    for i, (label, prefix) in enumerate(zip(labels, callback_prefix)):
        status = "[✅]" if state[i] == "1" else "[❌]"
        callback_data = f"notify_set_{1 - int(state[i])}_{prefix}"
        keyboard.row(InlineKeyboardButton(text=f"{status} {label}", callback_data=callback_data))
    
    keyboard.row(InlineKeyboardButton(text="Подтвердить 🙌", callback_data="approve_adding"))
    keyboard.row(InlineKeyboardButton(text="Отмена 🙅‍♂️", callback_data="cancel_states"))

    return keyboard.as_markup()

notify_keyboards = {
    tuple(map(bool, map(int, f"{i:03b}"))): create_notify_keyboard(f"{i:03b}")
    for i in range(8)
}

def choose_correct_notify_keyboard(data):
    return notify_keyboards.get(
        (data['notify_before_week'], data['notify_before_day'], data['notify_in_today']),
        cancel_keyboard
    )

# Клавиатура отмены states
cancel_keyboard = InlineKeyboardBuilder()
cancel_keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_states"))
cancel_keyboard = cancel_keyboard.as_markup()

months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# Клавиатура выбора месяца для отображения - вправо-влево
def get_month_keyboard(current_month: int) -> InlineKeyboardMarkup:
    prev_month = current_month - 1 if current_month > 1 else 12
    next_month = current_month + 1 if current_month < 12 else 1
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"⬅️ {months[(current_month - 2) % 12]}", callback_data=f"list_select_month_{prev_month}"),
        InlineKeyboardButton(text=f"        ", callback_data=f"list_select_month_none"),
        InlineKeyboardButton(text=f"➡️ {months[current_month % 12]}", callback_data=f"list_select_month_{next_month}")
    )
    
    builder.row(InlineKeyboardButton(text=f"Выбрать месяц", callback_data=f"list_select_month_list"))
    builder.row(InlineKeyboardButton(text=f"Удалить дни рождения", callback_data=f"list_select_month_{current_month}_update"))
    builder.row(InlineKeyboardButton(text="Показать все дни рождения", callback_data="list_select_month_all"))
    
    return builder.as_markup()

# Клавиатура выбора месяца для отображения - списком
list_months = InlineKeyboardBuilder()
list_months_buttons = [[InlineKeyboardButton(text=f"{months[j]}", callback_data=f"list_select_month_{j+1}") for j in range(i*3, i*3 + 3)] for i in range(4)]
for i in range(4):
    list_months.row(*list_months_buttons[i])
list_months = list_months.as_markup()

# Клавиатура выбора записи
def get_entries_list(data: list, month: int, show_choose_buttons: bool = False, koef: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    list_intersected = [x for x in list(range(koef * 20, koef * 20 + 20)) if x in list(range(len(data)))]
    for i in list_intersected:
        builder.row(InlineKeyboardButton(text=f"{data[i]["name"]}", callback_data=f"del_month={month}_{data[i]["id"]}"))
    if show_choose_buttons:
        buttons_local = []
        if koef > 0:
            buttons_local.append(InlineKeyboardButton(text=f"⬅️", callback_data=f"del_month={month}_{koef - 1}_left"))
            if not koef * 20 + 20 > len(data):
                buttons_local.append(InlineKeyboardButton(text=f"   ", callback_data=f"del_none"))
                buttons_local.append(InlineKeyboardButton(text=f"➡️", callback_data=f"del_month={month}_{koef + 1}_right"))
        else:
            buttons_local.append(InlineKeyboardButton(text=f"➡️", callback_data=f"del_month={month}_{koef + 1}_right"))
        builder.row(*buttons_local)
    builder.row(InlineKeyboardButton(text=f"Назад к списку", callback_data=f"del_month={month}_tolist"))
    return builder.as_markup()

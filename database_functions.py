import os
import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool

# Настройки
DB_HOST = os.getenv("DATABASE_HOST")
DB_PORT = os.getenv("DATABASE_PORT")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_BASE = os.getenv("POSTGRES_DB")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Подключение к СУБД и создание БД, если не существует
def init_db():
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname="postgres", user=DB_USER, password=DB_PASSWORD)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_BASE}'")
        exists = cur.fetchone()
        if not exists:
            cur.execute(f"CREATE DATABASE {DB_BASE}")
        cur.close()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка подключения к СУБД и создания БД: {e}")
    finally:
        conn.close()

try:
    pool = SimpleConnectionPool(1, 20, host=DB_HOST, port=DB_PORT, dbname=DB_BASE, user=DB_USER, password=DB_PASSWORD)
except UnicodeDecodeError:
    init_db()
    pool = SimpleConnectionPool(1, 20, host=DB_HOST, port=DB_PORT, dbname=DB_BASE, user=DB_USER, password=DB_PASSWORD)


def get_conn():
    return pool.getconn()

def release_conn(conn):
    pool.putconn(conn)

# Создание таблицы, если не существует
def create_table():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS birthdays (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    birthday DATE NOT NULL,
                    store_year BOOLEAN DEFAULT TRUE,
                    notify_before_week BOOLEAN DEFAULT TRUE,
                    notify_before_day BOOLEAN DEFAULT TRUE,
                    notify_in_today BOOLEAN DEFAULT TRUE
                )
            ''')
            conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при создании таблицы: {e}")
    finally:
        release_conn(conn)

# Добавление дня рождения
def add_birthday(user_id, name, birthday, store_year, notify_before_week, notify_before_day, notify_in_today) -> int:
    ok = False
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO birthdays (
                        user_id, 
                        name, 
                        birthday, 
                        store_year, 
                        notify_before_week, 
                        notify_before_day, 
                        notify_in_today) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (user_id, name, birthday, store_year, notify_before_week, notify_before_day, notify_in_today))
            conn.commit()
            ok = True
    except Exception as e:
        logging.error(f"Ошибка сохранения данных. Параметры добавления пользователя: "\
                      f"user_id={user_id}, "\
                      f"name={name}, "\
                      f"birthday={birthday}, "\
                      f"store_year={store_year},"\
                      f"notify_before_week={notify_before_week},"\
                      f"notify_before_day={notify_before_day},"\
                      f"notify_in_today={notify_in_today}.\n\nОшибка: {e}")
    finally:
        release_conn(conn)
    return ok

# Удаление дня рождения
def del_birthday(user_id, id) -> int:
    ok = False
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM birthdays WHERE id=(%s) AND user_id=(%s)""",
                        (id, user_id))
            conn.commit()
            ok = True
    except Exception as e:
        logging.error(f"Ошибка удаления данных. Параметры добавления пользователя: "\
                      f"user_id={user_id}, "\
                      f"id={id}. Ошибка: {e}")
    finally:
        release_conn(conn)
    return ok

# Список дней рождения пользователя
def list_birthdays(user_id: int, month: int = 0) -> list:
    result = []
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            if month == 0:
                cur.execute(
                    """
                    SELECT * FROM birthdays
                    WHERE user_id = %s
                    ORDER BY EXTRACT(MONTH FROM birthday), EXTRACT(DAY FROM birthday)
                    """,
                    (user_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM birthdays
                    WHERE user_id = %s AND EXTRACT(MONTH FROM birthday) = %s
                    ORDER BY EXTRACT(DAY FROM birthday)
                    """,
                    (user_id, month),
                )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logging.error(f"Ошибка получения списка дней рождения пользователя {user_id}. Ошибка: {e}")
    finally:
        release_conn(conn)
    return result

# Список дней рождения всех пользователей сегодня и в +delta дней
def list_birthdays_all(days_delta: int = 0) -> list:
    result = []
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            match days_delta:
                case 0:
                    cur.execute(
                        """
                        SELECT user_id, array_to_string(array_agg(name), ', ') as name FROM birthdays
                        WHERE EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE)
                        AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE)
                        AND notify_in_today
                        GROUP BY user_id;
                        """,
                    )
                case 1:
                    cur.execute(
                        """
                        SELECT user_id, array_to_string(array_agg(name), ', ') as name FROM birthdays
                        WHERE EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE + 1)
                        AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE + 1)
                        AND notify_before_day
                        GROUP BY user_id
                        """,
                    )
                case 7:
                    cur.execute(
                        """
                        SELECT user_id, array_to_string(array_agg(name), ', ') as name FROM birthdays
                        WHERE EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE + 7)
                        AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE + 7)
                        AND notify_before_week
                        GROUP BY user_id
                        """,
                    )
                case _:
                    cur.execute(
                        """
                        SELECT user_id, array_to_string(array_agg(name), ', ') as name FROM birthdays
                        WHERE EXTRACT(DAY FROM birthday) = EXTRACT(DAY FROM CURRENT_DATE + %s)
                        AND EXTRACT(MONTH FROM birthday) = EXTRACT(MONTH FROM CURRENT_DATE + %s)
                        GROUP BY user_id
                        """,
                        (days_delta, days_delta),
                    )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logging.error(f"Ошибка получения списка дней рождения пользователя. Ошибка: {e}")
    finally:
        release_conn(conn)
    return result


create_table()
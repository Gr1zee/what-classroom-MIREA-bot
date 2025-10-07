import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from icalendar import Calendar
from datetime import datetime, date
import pytz
from dateutil.rrule import rrulestr
import requests
from dotenv import load_dotenv
from os import getenv

load_dotenv()
# токен бота
BOT_TOKEN = getenv("BOT_TOKEN")
CALENDAR_URL = getenv("CALENDAR_URL")

def plural(n):
    if n % 10 == 1 and n % 100 != 11:
        return "событие"
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "события"
    else:
        return "событий"

def sort_key(event):
    if event['is_all_day']:
        # События на весь день — в начало (время 00:00 без tz)
        return (0, datetime.min)
    else:
        dt = event['start']
        # Приводим к naive, если нужно, или используем как есть
        if dt.tzinfo is not None:
            # Преобразуем в naive, убирая tzinfo (для сортировки достаточно даты и времени)
            return (1, dt.replace(tzinfo=None))
        else:
            return (1, dt)


def get_todays_events(calendar_data):
    tz = pytz.timezone('Europe/Moscow')
    today = date.today()

    cal = calendar_data

    events_today = []


    for event in cal.walk('VEVENT'):
        summary = str(event.get('summary', 'Без названия')).strip()
        location = str(event.get('location', '')).strip()
        dtstart = event.get('dtstart')
        if not dtstart:
            continue

        # Событие на весь день (например, "6 неделя")
        if dtstart.params.get('VALUE') == 'DATE':
            event_date = dtstart.dt
            if isinstance(event_date, date) and event_date == today:
                events_today.append({
                    'summary': summary,
                    'location': location,
                    'start': None,
                    'is_all_day': True
                })
            continue

        # Событие с временем
        start_dt = dtstart.dt
        if not isinstance(start_dt, datetime):
            continue

        rrule_prop = event.get('rrule')
        exdates = event.get('exdate')
        exdate_set = set()

        # Обработка EXDATE (исключённых дат)
        if exdates:
            exdate_list = exdates if isinstance(exdates, list) else [exdates]
            for exd in exdate_list:
                for dt in exd.dts:
                    d = dt.dt
                    exdate_set.add(d.date() if isinstance(d, datetime) else d)

        if not rrule_prop:
            # Однократное событие
            if start_dt.date() == today:
                events_today.append({
                    'summary': summary,
                    'location': location,
                    'start': start_dt,
                    'is_all_day': False
                })
        else:
            # Повторяющееся событие
            try:
                rrule_str = event['rrule'].to_ical().decode('utf-8')
                rule = rrulestr(rrule_str, dtstart=start_dt)
                for occ in rule:
                    occ_date = occ.date()
                    if occ_date > date(2025, 12, 31):  # ограничение семестра
                        break
                    if occ_date == today and occ_date not in exdate_set:
                        events_today.append({
                            'summary': summary,
                            'location': location,
                            'start': occ,
                            'is_all_day': False
                        })
                        break
            except Exception as e:
                print(f"⚠️ Ошибка обработки RRULE для '{summary}': {e}")


    return events_today


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_schedule_today():
    try:
        response = requests.get(CALENDAR_URL)
        response.raise_for_status()
        calendar_data = Calendar.from_ical(response.text)
        events = get_todays_events(calendar_data)
        return events
    except Exception as e:
        return [f"Ошибка при получении расписания: {e}"]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Нажмите /schedule, чтобы получить расписание на сегодня.")

@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    await message.answer("Получаю расписание на сегодня...")
    events = get_schedule_today()
    if events:
        word = plural(len(events))
        print(f"Сегодня ({date.today()}) у вас {len(events)} {word}:")
        for ev in events:
            if ev['is_all_day']:
                ...
            else:
                start_time = ev['start'].strftime('%H:%M')
                await message.answer(f"  🕒 {start_time} — {ev['summary']} | {ev['location']}")
    else:
        print("Сегодня занятий нет.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
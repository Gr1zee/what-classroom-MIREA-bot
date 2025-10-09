import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import logging
from os import getenv
from app.src.event_times_maker import event_maker


# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота (лучше из .env, но для примера — прямо здесь)
load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
EVENT_TIMES = ["12:57", "17:28", "23:50"]

sent_notifications = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

NOTIFIED_USERS = set()

# Команда /start — чтобы пользователь "подписался" на уведомления
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    NOTIFIED_USERS.add(user_id)
    await message.answer("✅ Вы подписаны на уведомления! Сообщения придут за 10 минут до событий.")

async def notification_scheduler(event_times):
    while True:
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)

        for time_str in event_times:
            print(time_str)
            target_time = datetime.strptime(time_str, "%H:%M").time()

            # Кандидаты: сегодня и завтра
            candidate_today = datetime.combine(today, target_time)
            candidate_tomorrow = datetime.combine(tomorrow, target_time)

            # Выбираем ближайшее будущее событие
            if candidate_today > now:
                event_dt = candidate_today
            else:
                event_dt = candidate_tomorrow

            notify_time = event_dt - timedelta(minutes=10)
            notification_key = (event_dt.date(), time_str)

            if notify_time <= now < event_dt and notification_key not in sent_notifications:
                sent_notifications.add(notification_key)
                for user_id in NOTIFIED_USERS:
                    try:
                        await bot.send_message(
                            user_id,
                            f"🔔 Напоминание! Кабинет: {event_times[time_str]}."
                        )
                    except Exception as e:
                        logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

        await asyncio.sleep(5)

# Запуск бота
async def main():
    event_times = event_maker()
    print(event_times)
    asyncio.create_task(notification_scheduler(event_times))
    await dp.start_polling(bot)
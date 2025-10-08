from datetime import datetime

from .calendar_parsing import get_schedule_today


def event_maker():
    events = get_schedule_today()
    event_times = {}
    for ev in events:
        if ev['is_all_day']: continue
        target_time = ev['start'].strftime('%H:%M')
        event_times[target_time] = ev['location']
    return event_times


def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M").time()
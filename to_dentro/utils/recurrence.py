from datetime import date, datetime, timedelta
from dateutil import rrule
from to_dentro.models.event_recurrence import RecurrenceTypes, WeeksInterval
from to_dentro.models.event_recurrence_weekday import WeekDays

def generate_recurrence_dates(
    start_date: date,
    end_date: date | None,
    rec_type: RecurrenceTypes,
    weeks_interval: WeeksInterval | None = None,
    day_of_month: int | None = None,
    weekdays: list[WeekDays] | None = None
) -> list[date]:
    """
    Gera uma lista de datas para um evento recorrente baseado na regra fornecida.
    O limite máximo de geração é de 1 ano a partir de start_date.
    """
    limit_date = start_date + timedelta(days=365)
    final_end_date = min(end_date, limit_date) if end_date else limit_date

    if final_end_date < start_date:
        final_end_date = start_date

    dt_start = datetime.combine(start_date, datetime.min.time())
    dt_until = datetime.combine(final_end_date, datetime.max.time())

    freq_map = {
        RecurrenceTypes.DAILY: rrule.DAILY,
        RecurrenceTypes.WEEKLY: rrule.WEEKLY,
        RecurrenceTypes.MONTHLY: rrule.MONTHLY,
        RecurrenceTypes.YEARLY: rrule.YEARLY,
    }
    freq = freq_map.get(rec_type, rrule.DAILY)

    kwargs = {
        "freq": freq,
        "dtstart": dt_start,
        "until": dt_until,
    }

    if rec_type == RecurrenceTypes.WEEKLY:
        if weeks_interval:
            kwargs["interval"] = 1 if weeks_interval.name == "ONE" else 2

        if weekdays:
            weekday_map = {
                WeekDays.MONDAY: rrule.MO,
                WeekDays.TUESDAY: rrule.TU,
                WeekDays.WEDNESDAY: rrule.WE,
                WeekDays.THURSDAY: rrule.TH,
                WeekDays.FRIDAY: rrule.FR,
                WeekDays.SATURDAY: rrule.SA,
                WeekDays.SUNDAY: rrule.SU,
            }
            kwargs["byweekday"] = [weekday_map[wd] for wd in weekdays if wd in weekday_map]

    elif rec_type == RecurrenceTypes.MONTHLY:
        if day_of_month:
            kwargs["bymonthday"] = day_of_month

    rule = rrule.rrule(**kwargs)
    dates = [dt.date() for dt in rule]

    if not dates:
        dates = [start_date]

    if start_date not in dates:
        dates.insert(0, start_date)
        dates.sort()

    return dates

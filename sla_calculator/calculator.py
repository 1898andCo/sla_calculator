import pendulum
import holidays as pyholidays


class SLA_Calculator:
    def __init__(self, *args, **kwargs):
        self.open_hour = kwargs.get("open_hour", 9)
        self.close_hour = kwargs.get("close_hour", 17)
        self.holidays = kwargs.get("holidays", [])

    def _is_weekend(self, start_time: pendulum.DateTime):
        return start_time.day_of_week in (pendulum.SUNDAY, pendulum.SATURDAY)

    def _is_holiday(self, start_time: pendulum.DateTime):
        return (
            pendulum.date(start_time.year, start_time.month, start_time.day)
            in self.holidays
        )

    def _is_working_day(self, start_time: pendulum.DateTime):
        return not (self._is_weekend(start_time) or self._is_holiday(start_time))

    def check_working_days(self, start_time: pendulum.DateTime):
        while (
            not self._is_working_day(start_time) or start_time.hour >= self.close_hour
        ):
            start_time = start_time.add(days=1)
            start_time = pendulum.datetime(
                start_time.year,
                start_time.month,
                start_time.day,
                self.open_hour,
                0,
                0,
                tz=pendulum.local_timezone(),
            )
        return start_time

    def calculate(
        self,
        start_time,
        open_hour,
        close_hour,
        country_name="US",
        sla_in_hours=4,
        province=None,
        state=None,
    ):
        sla_time = None
        sla_in_minutes = sla_in_hours * 60
        start_time = (
            start_time
            if isinstance(start_time, pendulum.DateTime)
            else pendulum.parse(start_time, tz=pendulum.local_timezone())
        )

        country_holidays = list(
            pyholidays.CountryHoliday(
                country_name, years=[start_time.year], prov=province, state=state
            ).keys()
        )
        start_time = self.check_working_days(start_time)

        open_time = pendulum.datetime(
            start_time.year,
            start_time.month,
            start_time.day,
            open_hour,
            0,
            0,
            tz=pendulum.local_timezone(),
        )
        close_time = pendulum.datetime(
            start_time.year,
            start_time.month,
            start_time.day,
            close_hour,
            0,
            0,
            tz=pendulum.local_timezone(),
        )
        if start_time < open_time:
            start_time = open_time
        elif start_time > close_time:
            start_time = open_time.add(days=1)

            start_time = self.check_working_days(
                start_time, country_holidays, open_hour
            )

            open_time = pendulum.datetime(
                start_time.year,
                start_time.month,
                start_time.day,
                open_hour,
                0,
                0,
                tz=pendulum.local_timezone(),
            )
            close_time = pendulum.datetime(
                start_time.year,
                start_time.month,
                start_time.day,
                close_hour,
                0,
                0,
                tz=pendulum.local_timezone(),
            )

        time_left_today = start_time.diff(close_time).in_minutes()
        if time_left_today >= sla_in_minutes:
            sla_time = start_time.add(minutes=sla_in_minutes)
        else:
            tomorrow_minutes = sla_in_minutes - time_left_today
            start_time = open_time.add(days=1)
            while tomorrow_minutes > time_left_today:
                start_time = self.check_working_days(
                    start_time, country_holidays, open_hour
                )
                open_time = pendulum.datetime(
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    open_hour,
                    0,
                    0,
                    tz=pendulum.local_timezone(),
                )
                close_time = pendulum.datetime(
                    start_time.year,
                    start_time.month,
                    start_time.day,
                    close_hour,
                    0,
                    0,
                    tz=pendulum.local_timezone(),
                )
                time_left_today = start_time.diff(close_time).in_minutes()
                if time_left_today >= sla_in_minutes:
                    sla_time = start_time.add(minutes=tomorrow_minutes)
                    break
                else:
                    tomorrow_minutes = tomorrow_minutes - time_left_today
                    start_time = open_time.add(days=1)
            if not sla_time:
                sla_time = start_time.add(minutes=tomorrow_minutes)

        return sla_time

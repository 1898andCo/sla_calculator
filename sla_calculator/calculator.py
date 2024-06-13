from datetime import time
import pendulum
import holidays as pyholidays


class SLA_Calculator:
    """Calculates the SLA time based on the start time, open hour, close hour, country, and SLA in hours.


    Keyword Args:
        open_hour (int): The hour the business opens. Defaults to 9.
        close_hour (int): The hour the business closes. Defaults to 17.
        holidays (list): A list of manual holidays. Defaults to [].
        country_name (str): The country name. Defaults to None. Can be two-letter or three-letter country code.
        province (str): The province or state name. Defaults to None.
        state (str): The state name. Defaults to None.

    If no country name is passed in, no holidays will be considered other than the manual holidays passed in.

    Example:
        sla_calc = SLA_Calculator(
            open_hour=9,
            close_hour=17,
            holidays=["2024-01-01"],
            country_name="US",
            province="MO",
            state="MO",
            timezone="America/Chicago",
        )

    """

    def __init__(self, *args, **kwargs):
        self.open_hour = kwargs.get("open_hour", 9)
        self.close_hour = kwargs.get("close_hour", 17)  # what a way to make a living
        self.holidays = []
        # get holidays for the country and province/state
        if kwargs.get("country_name"):
            self.holidays = list(
                pyholidays.CountryHoliday(
                    kwargs.get("country_name"),
                    years=[pendulum.now().year],
                    prov=kwargs.get("province"),
                    state=kwargs.get("state"),
                ).keys()
            )
        # add any manual holidays
        manual_holidays = kwargs.get("holidays", [])
        if kwargs.get("timezone"):
            pendulum.set_local_timezone(kwargs.get("timezone"))
        else:
            pendulum.set_local_timezone()
        if not isinstance(manual_holidays, list):
            manual_holidays = [manual_holidays]
        self.holidays.extend(manual_holidays)

    def _wrap_pendulum_datetime(self, start_time: pendulum.DateTime | str):
        if isinstance(start_time, str):
            tm = pendulum.parse(start_time)
            t = pendulum.datetime(
                tm.year,  # type: ignore [attr-defined]
                tm.month,  # type: ignore [attr-defined]
                tm.day,  # type: ignore [attr-defined]
                tm.hour,  # type: ignore [attr-defined]
                tm.minute,  # type: ignore [attr-defined]
                tm.second,  # type: ignore [attr-defined]
                tz=tm.timezone_name,  # type: ignore [attr-defined]
            )
        else:
            t = start_time

        return t

    def _is_weekend(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        return start_time.day_of_week in (pendulum.SUNDAY, pendulum.SATURDAY)

    def _is_holiday(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        return (
            pendulum.date(start_time.year, start_time.month, start_time.day)
            in self.holidays
        )

    def _is_working_day(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        return not (self._is_weekend(start_time) or self._is_holiday(start_time))

    def _next_working_day(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        while not self._is_working_day(start_time):
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

    def _next_day_open_time(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        start_time = self._next_working_day(start_time)
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

    def check_working_days(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        while (
            not self._is_working_day(start_time) or start_time.hour >= self.close_hour
        ):
            start_time = self._next_working_day(start_time)
        return start_time

    def _calculate_time_left_today(self, start_time):
        start_time = self._wrap_pendulum_datetime(start_time)
        close_time = pendulum.datetime(
            start_time.year,
            start_time.month,
            start_time.day,
            self.close_hour,
            0,
            0,
            tz=pendulum.local_timezone(),
        )
        return start_time.diff(close_time).in_minutes()

    def calculate(
        self,
        start_time,
        sla_in_minutes=4,
    ):
        sla_time = None
        start_time = self._wrap_pendulum_datetime(start_time)

        start_time = self.check_working_days(start_time)

        # if before open time, set to open time
        if start_time.hour < self.open_hour:
            start_time = pendulum.datetime(
                start_time.year,
                start_time.month,
                start_time.day,
                self.open_hour,
                0,
                0,
                tz=pendulum.local_timezone(),
            )
        time_left_today = self._calculate_time_left_today(start_time)
        if time_left_today >= sla_in_minutes:
            sla_time = start_time.add(minutes=sla_in_minutes)
        else:
            next_day = self._next_day_open_time(start_time)
            sla_in_minutes = sla_in_minutes - time_left_today 
            return self.calculate(next_day, sla_in_minutes=sla_in_minutes)
        return sla_time

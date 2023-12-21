import datetime
import enum
import re

import dateparser

__all__ = ("ConversionMode", "convert_time")

import pytz


class ConversionMode(int, enum.Enum):
    """All possible time conversion modes."""

    RELATIVE = 0
    ABSOLUTE = 1


def convert_time(
    time_str: str,
    *,
    now: datetime.datetime | None = None,
    conversion_mode: ConversionMode | None = None,
    future_time: bool = False,
) -> datetime.datetime:
    """Try converting a string of human-readable time to a datetime object."""
    time_str = str(time_str)
    if not conversion_mode or conversion_mode == ConversionMode.RELATIVE:
        # Relative time conversion Get any pair of <number><word> with a single optional space in between,
        # and return them as a dict (sort of)
        time_regex = re.compile(r"(\d+(?:[.,]\d+)?)\s?(\w+)")
        time_letter_dict = {
            "h": 3600,
            "s": 1,
            "m": 60,
            "d": 86400,
            "w": 86400 * 7,
            "M": 86400 * 30,
            "Y": 86400 * 365,
            "y": 86400 * 365,
        }
        time_word_dict = {
            "hour": 3600,
            "second": 1,
            "minute": 60,
            "day": 86400,
            "week": 86400 * 7,
            "month": 86400 * 30,
            "year": 86400 * 365,
            "sec": 1,
            "min": 60,
        }
        matches = time_regex.findall(time_str)
        time = 0.0

        for input_str, category in matches:
            input_str = input_str.replace(",", ".")
            # Replace commas with periods to correctly register decimal places
            # If this is a single letter

            if len(category) == 1:
                if value := time_letter_dict.get(category):
                    time += value * float(input_str)

            else:
                for string, value in time_word_dict.items():
                    if (
                        category.lower() == string or category.lower()[:-1] == string
                    ):  # Account for plural forms of the word
                        time += value * float(input_str)
                        break

        if time > 0:  # If we found time
            if now:
                return now + datetime.timedelta(seconds=time)

            return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=time)

        time_parsed = dateparser.parse(time_str, settings={"PREFER_DATES_FROM": "future"})

        if time_parsed:
            return time_parsed

        if conversion_mode == ConversionMode.RELATIVE:
            raise ValueError("Failed time conversion. (relative)")

    if not conversion_mode or conversion_mode == ConversionMode.ABSOLUTE:
        timezone = "UTC"

        time_parsed = dateparser.parse(
            time_str,
            settings={"TIMEZONE": timezone, "RETURN_AS_TIMEZONE_AWARE": True},
            date_formats=["%d.%m.%Y", "%d.%m.%Y %H:%M:%S"],
        )

        if not time_parsed:
            raise ValueError("Time could not be parsed. (absolute)")

        if future_time and time_parsed < datetime.datetime.now(pytz.UTC):
            raise ValueError("Time is not in the future!")

        return time_parsed.astimezone(pytz.UTC)

    raise ValueError("Time conversion failed.")

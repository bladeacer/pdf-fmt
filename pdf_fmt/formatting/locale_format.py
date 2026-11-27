"""Locale-aware date, number and currency formatting hooks backed by Babel."""

from datetime import date, datetime

from babel.core import Locale
from babel.dates import format_date
from babel.numbers import format_currency, format_decimal


def _parse(locale: str) -> Locale:
    """Converts a BCP 47 tag to a Babel locale."""
    return Locale.parse(locale, sep='-')


def format_locale_date(value: date | datetime, locale: str) -> str:
    """Formats a date for a BCP 47 locale."""
    return format_date(value, locale=_parse(locale))


def format_locale_number(value: float, locale: str) -> str:
    """Formats a decimal number for a BCP 47 locale."""
    return format_decimal(value, locale=_parse(locale))


def format_locale_currency(value: float, currency: str, locale: str) -> str:
    """Formats a currency amount for a BCP 47 locale."""
    return format_currency(value, currency, locale=_parse(locale))

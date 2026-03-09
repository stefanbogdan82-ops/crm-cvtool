# app/services/render/dates.py

from __future__ import annotations
import calendar

def format_yyyy_or_yyyymm(value: str | None) -> str:
    """
    Input: "2024" or "2024-02" or None
    Output: "2024" or "Feb 2024" or ""
    """
    if not value:
        return ""
    if len(value) == 4 and value.isdigit():
        return value
    if len(value) == 7 and value[4] == "-":
        yyyy = value[:4]
        mm = int(value[5:7])
        return f"{calendar.month_abbr[mm]} {yyyy}"
    return value  # fallback

def make_period_label(start_date: str | None, end_date: str | None) -> str:
    """
    Returns a compact label like "2023–2025" or "2023–Present".
    Prefers year-only display.
    """
    def year(v: str | None) -> str | None:
        if not v:
            return None
        return v[:4] if len(v) >= 4 else None

    ys = year(start_date)
    ye = year(end_date)
    if ys and ye:
        return f"{ys}–{ye}"
    if ys and not ye:
        return f"{ys}–Present"
    return ""

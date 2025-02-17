# utils.py

"""
This module holds various utility functions for the Nextdoor bot.
They primarily convert variable formats, provide convenience helpers,
and generally improve code quality.
"""

# -----------------------------
# IMPORTS
# -----------------------------
from datetime import datetime, timedelta  # Used for time calculations

# ---------------------------------------------------------------------------
# 1. Convert relative time to absolute
# ---------------------------------------------------------------------------
def convert_relative_time_to_absolute(relative_time):
    """
    Converts relative timestamps (e.g., '1 hr ago', '2 days ago')
    into absolute timestamps. Returns a string like 'MM/DD/YY, HH:MM'.

    Args:
        relative_time (str): e.g. "1 hr ago" or "2 days ago".

    Returns:
        str: The converted date/time in 'MM/DD/YY, HH:MM' format.
    """

    # 1) Get the current time
    current_time = datetime.now()

    try:
        # 2) Check the format of the relative time
        if "min ago" in relative_time:
            minutes = int(relative_time.split()[0])
            absolute_time = current_time - timedelta(minutes=minutes)
        elif "hr ago" in relative_time:
            hours = int(relative_time.split()[0])
            absolute_time = current_time - timedelta(hours=hours)
        elif "day ago" in relative_time or "days ago" in relative_time:
            days = int(relative_time.split()[0])
            absolute_time = current_time - timedelta(days=days)
        else:
            # 3) If we don't recognize the format, default to now
            print(f"⚠️ Unrecognized date format: {relative_time}. Using current time.")
            return current_time.strftime("%m/%d/%y, %H:%M")

        # 4) Return the converted time in 'MM/DD/YY, HH:MM'
        return absolute_time.strftime("%m/%d/%y, %H:%M")

    except Exception as e:
        # 5) If anything goes wrong, default to now
        print(f"⚠️ Error converting relative time '{relative_time}': {e}")
        return current_time.strftime("%m/%d/%y, %H:%M")








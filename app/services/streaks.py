from datetime import date, timedelta

from app.models import User


def record_activity(user: User, today: date) -> None:
    last = user.last_active_on
    if last is not None and today <= last:
        return

    if last == today - timedelta(days=1):
        user.current_streak += 1
    else:
        user.current_streak = 1

    user.longest_streak = max(user.longest_streak, user.current_streak)
    user.last_active_on = today


def visible_streak(user: User, today: date) -> int:
    """
    The stored number only counts if the last practice day was today or yesterday.
    Nothing resets it at midnight, so after a gap it is stale until the next quiz.
    """
    if user.last_active_on in (today, today - timedelta(days=1)):
        return user.current_streak

    return 0

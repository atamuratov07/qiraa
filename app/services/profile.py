from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Attempt, Passage, User
from app.services.streaks import visible_streak
from app.timeutils import local_day
from app.views import CalendarDay, ProfilePage, ProfileStats

CALENDAR_DAYS = 35
RECENT_LIMIT = 10


def profile_stats(db: Session, user: User) -> ProfileStats:
    attempts, answered, correct, passages_done = db.execute(
        select(
            func.count(Attempt.id),
            func.sum(Attempt.total),
            func.sum(Attempt.score),
            func.count(Attempt.passage_id.distinct()),
        ).where(Attempt.user_id == user.id, Attempt.submitted_at.is_not(None))
    ).one()

    answered = answered or 0
    correct = correct or 0
    passages_total = db.scalar(select(func.count(Passage.id))) or 0

    return ProfileStats(
        attempts=attempts,
        answered=answered,
        accuracy=round(100 * correct / answered) if answered else None,
        passages_done=passages_done,
        passages_total=passages_total,
    )


def activity_calendar(db: Session, user: User, now: datetime) -> list[CalendarDay]:
    """Submitted quizzes per local day for the last CALENDAR_DAYS days, oldest first.

    Counted in Python: grouping by *Tashkent* date in SQL needs timezone functions that
    differ between Postgres and SQLite, and there are only a few rows.
    One extra day is fetched so a quiz just after local midnight 35 days ago isn't missed.
    """
    today = local_day(now)
    submitted = db.scalars(
        select(Attempt.submitted_at).where(
            Attempt.user_id == user.id,
            Attempt.submitted_at >= now - timedelta(days=CALENDAR_DAYS + 1),
        )
    ).all()
    per_day = Counter(local_day(moment) for moment in submitted if moment is not None)
    days = [today - timedelta(days=n) for n in range(CALENDAR_DAYS - 1, -1, -1)]

    return [CalendarDay(date=day, count=per_day[day]) for day in days]


def recent_attempts(db: Session, user: User) -> list[Attempt]:
    return list(
        db.scalars(
            select(Attempt)
            .where(Attempt.user_id == user.id, Attempt.submitted_at.is_not(None))
            .options(selectinload(Attempt.passage))
            .order_by(Attempt.submitted_at.desc())
            .limit(RECENT_LIMIT)
        ).all()
    )


def profile_context(
    db: Session, user: User, now: datetime, *, delete_error: str | None = None
) -> ProfilePage:
    return {
        "user": user,
        "streak": visible_streak(user, local_day(now)),
        "longest_streak": user.longest_streak,
        "stats": profile_stats(db, user),
        "recent": recent_attempts(db, user),
        "calendar": activity_calendar(db, user, now),
        "delete_error": delete_error,
    }

"""Put a few sample passages into the database.

    uv run python -m app.seed             # add passages whose slug isn't in the database yet
    uv run python -m app.seed --replace   # delete and re-insert them (after editing PASSAGES below)

Point it at Neon for one run by setting DATABASE_URL just for that command:
    DATABASE_URL="postgresql://..." uv run python -m app.seed        (macOS / Linux)
    $env:DATABASE_URL="postgresql://..."; uv run python -m app.seed  (Windows PowerShell)

Temporary: in step 7 the YAML import replaces this file. The data below already uses
the same shape as the YAML files will, with "answer" = number of the correct option, from 1.
"""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Option, Passage, Question

PASSAGES = [
    {
        "slug": "a2-fi-alsouq",
        "title": "في السوق",
        "level": "A2",
        "text": (
            "ذهبت فاطمة يوم الجمعة إلى السوق مع أمها. اشترت فاطمة كيلوغرامًا من التفاح وثلاثَ "
            "برتقالات. وسألت أمها البائع: «بكم كيلو الطماطم؟» فقال البائع: «بعشرة دراهم». "
            "فاشترت الأم كيلوغرامين من الطماطم.\n\n"
            "بعد ذلك ذهبتا إلى محل الملابس، واشترت فاطمة قميصًا أزرقَ لأخيها الصغير، لأن عيد "
            "ميلاده يوم السبت. ثم رجعت فاطمة وأمها إلى البيت في الساعة الواحدة ظهرًا."
        ),
        "translation_ru": (
            "В пятницу Фатима пошла на рынок с мамой. Фатима купила килограмм яблок и три "
            "апельсина. Её мама спросила продавца: «Почём килограмм помидоров?» Продавец "
            "ответил: «Десять дирхамов». И мама купила два килограмма помидоров.\n\n"
            "После этого они пошли в магазин одежды, и Фатима купила синюю рубашку своему "
            "младшему брату, потому что у него день рождения в субботу. Потом Фатима и её мама "
            "вернулись домой в час дня."
        ),
        "glossary": {
            "السوق": "рынок",
            "البائع": "продавец",
            "بكم": "почём? сколько стоит?",
            "الطماطم": "помидоры",
            "محل": "магазин, лавка",
            "الملابس": "одежда",
            "قميص": "рубашка",
            "أزرق": "синий",
        },
        "questions": [
            {
                "prompt": "متى ذهبت فاطمة إلى السوق؟",
                "options": ["يوم الخميس", "يوم السبت", "يوم الجمعة", "يوم الأحد"],
                "answer": 3,
                "explanation": "Первое предложение: «ذهبت فاطمة يوم الجمعة». Суббота — это день рождения брата.",
            },
            {
                "prompt": "كم دفعت الأم ثمنَ الطماطم؟",
                "options": ["عشرة دراهم", "عشرين درهمًا", "خمسة دراهم", "ثلاثين درهمًا"],
                "answer": 2,
                "explanation": "10 дирхамов за килограмм, а мама купила два (كيلوغرامين — двойственное число): 2 × 10 = 20.",
            },
            {
                "prompt": "لمن اشترت فاطمة القميص؟",
                "options": ["لأمها", "لنفسها", "لأبيها", "لأخيها الصغير"],
                "answer": 4,
                "explanation": "«قميصًا أزرقَ لأخيها الصغير» — для младшего брата.",
            },
            {
                "prompt": "لماذا اشترت فاطمة القميص؟",
                "options": [
                    "لأن القميص كان رخيصًا",
                    "لأن عيد ميلاد أخيها يوم السبت",
                    "لأن أمها طلبت منها ذلك",
                    "لأن قميصها القديم كان صغيرًا",
                ],
                "answer": 2,
                "explanation": "После لأن («потому что») идёт причина: «عيد ميلاده يوم السبت».",
            },
        ],
    },
    {
        "slug": "b1-alamal-an-bud",
        "title": "العمل عن بُعد",
        "level": "B1",
        "text": (
            "انتشر العمل عن ب\x1b[118;1:3uُعد انتشارًا واسعًا في السنوات الأخيرة، وأصبحت شركات كثيرة تسمح "
            "لموظفيها بالعمل من البيت يومين أو ثلاثة أيام في الأسبوع.\n\n"
            "يرى المؤيّدون أن العمل عن بعد يوفّر الوقت والمال، إذ لا يحتاج الموظف إلى السفر "
            "يوميًا إلى المكتب. كما يمنحه حرية أكبر في تنظيم يومه.\n\n"
            "أما المعارضون فيقولون إن العمل من البيت قد يؤدي إلى الشعور بالعزلة، لأن الموظف "
            "يفقد التواصل اليومي مع زملائه.\n\n"
            "ويبدو أن كثيرًا من الشركات اختارت حلًّا وسطًا يجمع بين العمل في المكتب والعمل من "
            "البيت."
        ),
        "translation_ru": (
            "Удалённая работа в последние годы получила широкое распространение, и многие "
            "компании стали разрешать сотрудникам работать из дома два-три дня в неделю.\n\n"
            "Сторонники считают, что удалённая работа экономит время и деньги, поскольку "
            "сотруднику не нужно ежедневно ездить в офис. Кроме того, она даёт ему больше "
            "свободы в организации своего дня.\n\n"
            "Противники же говорят, что работа из дома может привести к чувству изоляции, "
            "потому что сотрудник теряет ежедневное общение с коллегами.\n\n"
            "Похоже, многие компании выбрали компромиссное решение, сочетающее работу в офисе и "
            "работу из дома."
        ),
        "glossary": {
            "عن بعد": "удалённо",
            "شركات": "компании",
            "المؤيدون": "сторонники",
            "يوفر": "экономит",
            "المكتب": "офис",
            "المعارضون": "противники",
            "العزلة": "изоляция, одиночество",
            "زملائه": "его коллеги",
            "حلا وسطا": "компромиссное решение",
        },
        "questions": [
            {
                "prompt": "كم يومًا في الأسبوع تسمح بعض الشركات بالعمل من البيت؟",
                "options": [
                    "يومًا واحدًا",
                    "كل أيام الأسبوع",
                    "أربعة أيام",
                    "يومين أو ثلاثة أيام",
                ],
                "answer": 4,
                "explanation": "«يومين أو ثلاثة أيام في الأسبوع» — первый абзац.",
            },
            {
                "prompt": "أيٌّ مما يلي من حجج المؤيدين؟",
                "options": [
                    "الشعور بالعزلة",
                    "توفير الوقت والمال",
                    "فقدان التواصل مع الزملاء",
                ],
                "answer": 2,
                "explanation": "Остальные варианты — аргументы противников (المعارضون).",
            },
            {
                "prompt": "ما المقصود بـ«حلًّا وسطًا» في الفقرة الأخيرة؟",
                "options": [
                    "العمل في المكتب فقط",
                    "الجمع بين العمل في المكتب والعمل من البيت",
                    "العمل من البيت فقط",
                ],
                "answer": 2,
                "explanation": "Текст сам объясняет: «يجمع بين العمل في المكتب والعمل من البيت».",
            },
            {
                "prompt": "ما موقف الكاتب من الموضوع؟",
                "options": [
                    "يؤيّد العمل عن بعد بقوة",
                    "يعارض العمل عن بعد بقوة",
                    "يعرض الرأيين دون أن ينحاز إلى أحدهما",
                ],
                "answer": 3,
                "explanation": "Автор приводит обе стороны и заканчивает нейтральным «ويبدو أن…».",
            },
        ],
    },
]


def check(data: dict) -> None:
    """Catch mistakes in PASSAGES before anything touches the database."""
    for n, q in enumerate(data["questions"], start=1):
        where = f"{data['slug']}, question {n}"
        assert len(q["options"]) >= 2, f"{where}: needs at least 2 options"
        assert 1 <= q["answer"] <= len(q["options"]), f"{where}: answer out of range"


def build(data: dict) -> Passage:
    """Turn one dict from PASSAGES into a Passage with its questions and options attached."""
    passage = Passage(
        slug=data["slug"],
        title=data["title"],
        level=data["level"],
        text=data["text"],
        translation_ru=data.get("translation_ru"),
        glossary=data.get("glossary", {}),
    )
    for q_pos, q in enumerate(data["questions"], start=1):
        question = Question(
            position=q_pos, prompt=q["prompt"], explanation=q.get("explanation")
        )
        for o_pos, text in enumerate(q["options"], start=1):
            question.options.append(
                Option(position=o_pos, text=text, is_correct=o_pos == q["answer"])
            )
        passage.questions.append(question)
    return passage


def seed(db: Session, replace: bool = False) -> None:
    for data in PASSAGES:
        check(data)
        existing = db.scalar(select(Passage).where(Passage.slug == data["slug"]))
        if existing is not None and not replace:
            print(f"skip     {data['slug']} (already in the database)")
            continue
        if existing is not None:
            db.delete(existing)
            db.flush()  # run the DELETE now, so the slug is free before the INSERT below
        db.add(build(data))
        print(
            f"{'replace' if existing else 'add':8} {data['slug']} ({len(data['questions'])} questions)"
        )
    db.commit()  # one transaction: if anything above failed, nothing was saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert sample passages.")
    _ = parser.add_argument(
        "--replace", action="store_true", help="re-insert passages that exist"
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        seed(db, replace=args.replace)


if __name__ == "__main__":
    main()

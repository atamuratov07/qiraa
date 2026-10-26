from app.passages.models import Passage


def test_display_title_is_the_title_when_there_is_one() -> None:
    assert Passage(title="نص", text="الفقرة الأولى.").display_title == "نص"


def test_display_title_falls_back_to_the_start_of_the_text() -> None:
    long = Passage(title=None, text="واحد اثنان ثلاثة أربعة خمسة ستة سبعة ثمانية")
    short = Passage(title=None, text="واحد\n\nاثنان")

    assert long.display_title == "واحد اثنان ثلاثة أربعة خمسة ستة…"
    assert short.display_title == "واحد اثنان"

"""Level 3: the question grid on the attempt and result pages (passage 1 has questions 1, 2)."""

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient


class GridReader(HTMLParser):
    """The first grid's links as target and state, e.g. '#q1 data-answered'. The attempt
    page has a second grid in its review."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.in_grid = False
        self.done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if tag == "nav" and "data-grid" in found and not self.done:
            self.in_grid = True
        elif tag == "a" and self.in_grid:
            state = [
                name if value is None else f'{name}="{value}"'
                for name, value in attrs
                if name.startswith("data-")
            ]
            self.links.append(" ".join([found["href"] or "", *state]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self.in_grid:
            self.in_grid = False
            self.done = True


def grid(page: str) -> list[str]:
    reader = GridReader()
    reader.feed(page)
    return reader.links


@pytest.mark.usefixtures("passage")
def test_the_grid_links_every_question_and_marks_answers(logged_in: TestClient) -> None:
    url = logged_in.post("/passages/1/attempts").headers["location"]
    attempt_id = url.rsplit("/", 1)[1]
    logged_in.put(f"/api/attempts/{attempt_id}/answers/2", json={"option_id": 21})

    page = logged_in.get(url).text

    assert grid(page) == ["#q1 data-current", "#q2 data-answered"]
    assert 'id="q1"' in page and 'id="q2"' in page

    logged_in.post(f"{url}/submit", data={"q1": "12", "q2": "21"})
    assert grid(logged_in.get(url).text) == [
        '#q1 data-result="wrong"',
        '#q2 data-result="wrong"',
    ]


@pytest.mark.usefixtures("passage")
def test_the_result_grid_marks_right_wrong_and_skipped(logged_in: TestClient) -> None:
    url = logged_in.post("/passages/1/attempts").headers["location"]
    logged_in.post(f"{url}/submit", data={"q2": "22"})  # q1 skipped, q2 right

    assert grid(logged_in.get(url).text) == [
        '#q1 data-result="skipped"',
        '#q2 data-result="right"',
    ]

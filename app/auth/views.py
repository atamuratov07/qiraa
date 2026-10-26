from typing import TypedDict


class LoginPage(TypedDict):
    """auth/login.html, GET and POST /login"""

    user: None  # base.html reads `user`; nobody is logged in on this page
    error: str | None
    username: str | None
    next: str


class SignupPage(TypedDict):
    """auth/signup.html, GET and POST /signup"""

    user: None
    error: str | None
    username: str | None
    code_required: bool

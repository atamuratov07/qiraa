from pydantic import BaseModel


class AnswerIn(BaseModel):
    option_id: int


class HeartbeatOut(BaseModel):
    elapsed_seconds: int

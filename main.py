from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Salam"}


passages = {
    "1": {
        "passage": "يبدأ يومي بالاستيقاظ مبكرًا لأداء صلاة الفجر. بعد ذلك، أتناول الإفطار وأشرب القهوة قبل",
        "questions": ["First", "Second", "Third"],
    },
    "2": {
        "passage": "الذهاب إلى العمل. أعمل لمدة ثماني ساعات وأتناول الغداء في المكتب. بعد العمل، أذهب",
        "questions": ["First", "Second", "Third"],
    },
    "3": {
        "passage": "إلى النادي لممارسة الرياضة. أعود إلى",
        "questions": ["First", "Second", "Third"],
    },
}


@app.get("/passages/{slug}")
def passage(slug: str):
    if slug not in passages:
        raise HTTPException(status_code=404, detail="Passage not found")

    return passages[slug]

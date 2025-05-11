# -*- coding: utf-8 -*-
"""Module for sentiment classification of feedback text using ML models."""
import re
from pathlib import Path
from typing import Dict

import joblib
import nltk
import uvicorn
from fastapi import Body, FastAPI, Query
from nltk.corpus import stopwords
from pydantic import BaseModel
from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()
nltk.download("stopwords")
russian_stopwords = stopwords.words("russian")


def lemmatize_and_remove_stopwords(text: str) -> str:
    """
    Lemmatize text and remove stopwords.

    Args:
        text: Input text to process

    Returns:
        Processed text with lemmas and without stopwords
    """
    words = re.findall(r"\b[а-яА-ЯёЁ]+\b", text.lower())
    lemmas = [
        morph.parse(word)[0].normal_form
        for word in words
        if word not in russian_stopwords
    ]
    return " ".join(lemmas)


app = FastAPI()


class FeedbackRequest(BaseModel):
    """Model for feedback analysis request data."""

    text: str


@app.post("/api/v1/predict/feedback", summary="Предсказание тональности комментария")
async def predict_feedback(
    model_version: int = Query(1, alias="Model"),
    request_data: FeedbackRequest = Body(...),
) -> Dict[str, str]:
    """
    Predict sentiment of feedback text.

    Args:
        model_version: Version of the model to use for prediction
        request_data: Feedback text for analysis

    Returns:
        Dictionary with sentiment prediction ("Плохой" or "Хороший")
    """
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "models"

    model_path = models_dir / "model_1_TF-IDFandLogReg.pkl"
    tfidf_path = models_dir / "tfidf_vectorizer.pkl"

    model = joblib.load(model_path)
    tfidf = joblib.load(tfidf_path)

    processed_text = lemmatize_and_remove_stopwords(request_data.text)
    new_review_tfidf = tfidf.transform([processed_text])

    prediction = model.predict(new_review_tfidf)
    return {"prediction": "Плохой" if prediction[0] == 1 else "Хороший"}


if __name__ == "__main__":
    uvicorn.run("control:app", host="0.0.0.0", port=8015, reload=True)

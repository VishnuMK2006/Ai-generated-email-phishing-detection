import os
import sys
import torch
import pickle
import re
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Append parent dir for feature_Extraction
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from feature_Extraction import extract_features_from_raw_email

app = FastAPI(title="XLM-RoBERTa Model API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.getenv("MODEL_PATH", "./xlmr_robert_base_model")
API_KEY = os.getenv("API_KEY", "my-secret-key")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    use_fast=False
)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()

id2label = model.config.id2label

# Load Header Model
header_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', 'email_spam_classifier_model_morden.pkl'))
with open(header_model_path, 'rb') as f:
    header_model_payload = pickle.load(f)
header_model = header_model_payload['model']
header_feature_names = header_model_payload['feature_names']


class PredictionRequest(BaseModel):
    text: str


class FullEmailRequest(BaseModel):
    raw_header: str
    body_text: str
    predict_body_if_phishing: bool = False


def _predict_body(text: str):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )
    with torch.no_grad():
        outputs = model(**inputs)
    predicted_class = torch.argmax(outputs.logits, dim=1).item()
    probabilities = torch.softmax(outputs.logits, dim=1)
    confidence = probabilities[0][predicted_class].item()
    predicted_label = id2label.get(predicted_class, f"Class {predicted_class}")
    return predicted_class, predicted_label, confidence


@app.get("/")
def home():
    return {
        "message": "XLM-RoBERTa API is running"
    }


@app.post("/predict")
def predict(
    request: PredictionRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    predicted_class, predicted_label, confidence = _predict_body(request.text)

    return {
        "text": request.text,
        "predicted_class": predicted_class,
        "predicted_label": predicted_label,
        "confidence": round(confidence, 4)
    }


@app.post("/analyze-email")
def analyze_email(
    request: FullEmailRequest,
    x_api_key: str = Header(None)
):
    # if x_api_key != API_KEY:
    #     raise HTTPException(
    #         status_code=401,
    #         detail="Invalid API key"
    #     )
        
    print("=== INCOMING JSON PAYLOAD ===")
    print(request.dict() if hasattr(request, 'dict') else request.model_dump())
    print("=============================")

    # 1. Extract base ML features from header
    raw_features = extract_features_from_raw_email(request.raw_header)
    
    # 2. Extract Authentication Headers explicitly for rules
    auth_matches = re.findall(r'(?:Authentication-Results|ARC-Authentication-Results):\s*([^\n\r]+)', request.raw_header, re.IGNORECASE)
    auth_str = " ".join(auth_matches).lower()
    
    spf_pass = "spf=pass" in auth_str
    dkim_pass = "dkim=pass" in auth_str
    has_auth = bool(auth_str.strip())
    
    df_input = pd.DataFrame([raw_features])
    for col in header_feature_names:
        if col not in df_input.columns:
            df_input[col] = 0
            
    X_test = df_input[header_feature_names]
    
    # 4. Get base ML Probability
    spam_prob = header_model.predict_proba(X_test)[0][1]
    
    # Manual Rule Penalty
    if not has_auth:
        spam_prob = min(1.0, spam_prob + 0.40)  # +40% penalty for no auth
    elif not spf_pass and not dkim_pass:
        spam_prob = min(1.0, spam_prob + 0.30)  # +30% penalty for failing both
        
    header_is_phishing = spam_prob >= 0.5
    
    final_is_phishing = False
    body_predicted_label = None
    body_confidence = None
    
    if not header_is_phishing or request.predict_body_if_phishing:
        # Predict body
        predicted_class, body_predicted_label, body_confidence = _predict_body(request.body_text)
        
        # Consider body model prediction
        if body_predicted_label.lower() == 'phishing' or 'phish' in body_predicted_label.lower():
            final_is_phishing = True
        elif header_is_phishing:
            final_is_phishing = True
    else:
        final_is_phishing = header_is_phishing
        
    final_label = "Phishing" if final_is_phishing else "Legitimate"
    
    if final_is_phishing and not request.predict_body_if_phishing and header_is_phishing:
        final_confidence = spam_prob
    elif body_confidence is not None:
        final_confidence = body_confidence
    else:
        final_confidence = spam_prob
        
    return {
        "predicted_label": final_label,
        "predicted_class": 1 if final_is_phishing else 0,
        "confidence": round(final_confidence, 4),
        "header_spam_probability": round(spam_prob, 4),
        "body_prediction": body_predicted_label
    }
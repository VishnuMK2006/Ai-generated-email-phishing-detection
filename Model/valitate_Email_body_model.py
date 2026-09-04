import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_PATH = "review/xlmr_robert_base_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

def predict_custom_email(subject, body, max_len=256):
    text = f"{subject} [SEP] {body}"

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=max_len
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)[0]
        pred_id = torch.argmax(probs).item()

    return {
        "intent_type": model.config.id2label[pred_id],
        "confidence": float(probs[pred_id]),
        "all_scores": {
            model.config.id2label[i]: float(probs[i])
            for i in range(len(probs))
        }
    }

subject = "Urgent: Un account 24 hrs-la suspend aagum – Verify pannunga"
body = """
Hi,

Ungaloda Axis Bank account-la oru suspicious login attempt nadanthirukku. Neenga login panna mudiyatha maari temporary-a restrict panni irukkom.

24 hours-kulla verify pannala na, un account permanently suspend aagidum.

Kindly below link-la click panni, ungaloda details verify pannikonga:
👉 https://axisbank-secure-verify.com/auth?token=9x2k5m

Ignore panna, ungaloda online banking services full-a block aagidum.

Thanks,
Axis Bank Security Team
"""

result = predict_custom_email(subject, body)
print(result)
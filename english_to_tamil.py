# import pandas as pd
# import glob
# import re
# import time
# from deep_translator import GoogleTranslator

# # ==================================================
# # CONFIG
# # ==================================================

# INPUT_PATTERN = "batch*.csv"

# PROTECTED_TERMS = [
#     "Microsoft 365","Office 365","SharePoint","OneDrive","Outlook","Teams",
#     "Azure","AWS","SAP","Oracle","ERP","CRM","HRMS","OTP","VPN","SSO","MFA",
#     "Payroll","Invoice","Password","Username","MDQ","Gas Daily","Index","FERC",
#     "CAISO","MWH","MW","LNG","PDF","Excel","Word","XML","CSV","XLS","XLSX",
#     "USER_ID","PW","LOGIN","API","JSON","HTML","HTTP","HTTPS","FTP","SQL",
#     "Java","Python","Linux","Windows","Oil",
# "Invoice",
# "Contract",
# "Agreement",
# "Report",
# "Schedule","Failover",
# "Upstream",
# "Downstream",
# "Master Physical",
# "GISB",
# "BNA",
# "FMPA"
# ]

# translator = GoogleTranslator(source="en", target="ta")

# # ==================================================
# # REGEX
# # ==================================================

# EMAIL_REGEX = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
# URL_REGEX = r'https?://\S+|www\.\S+'
# ACRONYM_REGEX = r'\b[A-Z]{2,}(?:-[A-Z0-9]+)?\b'

# # ==================================================
# # PROTECT TERMS
# # ==================================================

# def protect_text(text):
#     text = str(text)
#     mapping = {}
#     counter = 0

#     for term in sorted(PROTECTED_TERMS, key=len, reverse=True):
#         token = f"ZXQPROTECT{counter}ZXQ"
#         if term.lower() in text.lower():
#             pattern = re.compile(re.escape(term), re.IGNORECASE)
#             def replace(m):
#                 mapping[token] = m.group(0)
#                 return token
#             text = pattern.sub(replace, text)
#             counter += 1

#     for match in re.findall(EMAIL_REGEX, text):
#         token = f"KEEPTOKEN{counter}"
#         mapping[token] = match
#         text = re.sub(r'\b' + re.escape(match) + r'\b', token, text)
#         counter += 1

#     for match in re.findall(URL_REGEX, text):
#         token = f"KEEPTOKEN{counter}"
#         mapping[token] = match
#         text = re.sub(r'\b' + re.escape(match) + r'\b', token, text)
#         counter += 1

#     for match in set(re.findall(ACRONYM_REGEX, text)):
#         token = f"KEEPTOKEN{counter}"
#         mapping[token] = match
#         text = re.sub(r'\b' + re.escape(match) + r'\b', token, text)
#         counter += 1

#     return text, mapping

# # ==================================================
# # RESTORE TERMS
# # ==================================================

# def restore_text(text, mapping):
#     for token, value in mapping.items():
#         text = text.replace(token, value)
#     return text

# # ==================================================
# # TRANSLATE
# # ==================================================

# def translate_tamil(text):
#     if pd.isna(text):
#         return ""
#     text = str(text).strip()
#     if not text:
#         return ""
#     protected_text, mapping = protect_text(text)
#     try:
#         translated = translator.translate(protected_text)
#         translated = restore_text(translated, mapping)
#         time.sleep(0.15)
#         return translated
#     except Exception as e:
#         print("Translation Error:", e)
#         return text

# # ==================================================
# # PROCESS FILE
# # ==================================================

# def process_file(file_path):
#     batch_name = file_path.replace(".csv", "")
#     print(f"\nProcessing: {file_path}")
#     df = pd.read_csv(file_path)

#     if "subject_cleaned_2" in df.columns:
#         tamil_subjects = []
#         for idx, val in enumerate(df["subject_cleaned_2"].astype(str), start=1):
#             tamil_subjects.append(translate_tamil(val))
#             print(f"{batch_name}/{idx} subject done")
#         df["tamil_subject"] = tamil_subjects

#     if "body_cleaned_2" in df.columns:
#         tamil_bodies = []
#         for idx, val in enumerate(df["body_cleaned_2"].astype(str), start=1):
#             tamil_bodies.append(translate_tamil(val))
#             print(f"{batch_name}/{idx} body done")
#         df["tamil_body"] = tamil_bodies

#     output_file = file_path.replace(".csv", "_tamil.csv")
#     df.to_csv(output_file, index=False, encoding="utf-8-sig")
#     print("Saved:", output_file)

# # ==================================================
# # MAIN
# # ==================================================

# files = sorted(glob.glob(INPUT_PATTERN))
# print("Files found:", len(files))

# for file in files:
#     try:
#         process_file(file)
#     except Exception as e:
#         print(f"Failed {file}: {e}")

# print("\nAll batches completed.")


#Translate for chatgpt dataset


import pandas as pd
import json
import re
import time
from deep_translator import GoogleTranslator

INPUT_JSONL = "chatgpt_preprocessed.jsonl"
OUTPUT_JSONL = "chatgpt_translated_tamil.jsonl"

PROTECTED_TERMS = [
    "Microsoft 365","Office 365","SharePoint","OneDrive","Outlook","Teams",
    "Azure","AWS","SAP","Oracle","ERP","CRM","HRMS","OTP","VPN","SSO","MFA",
    "Payroll","Invoice","Password","Username","MDQ","Gas Daily","Index","FERC",
    "CAISO","MWH","MW","LNG","PDF","Excel","Word","XML","CSV","XLS","XLSX",
    "USER_ID","PW","LOGIN","API","JSON","HTML","HTTP","HTTPS","FTP","SQL",
    "Java","Python","Linux","Windows","Oil","Contract","Agreement","Report",
    "Schedule","Failover","Upstream","Downstream","Master Physical","GISB",
    "BNA","FMPA"
]

translator = GoogleTranslator(source="en", target="ta")

EMAIL_REGEX = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
URL_REGEX = r'https?://\S+|www\.\S+'
ACRONYM_REGEX = r'\b[A-Z]{2,}(?:-[A-Z0-9]+)?\b'

def protect_text(text):
    text = str(text)
    mapping = {}
    counter = 0

    for term in sorted(PROTECTED_TERMS, key=len, reverse=True):
        token = f"ZXQPROTECT{counter}ZXQ"
        if term.lower() in text.lower():
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            def replace(m):
                mapping[token] = m.group(0)
                return token
            text = pattern.sub(replace, text)
            counter += 1

    for match in re.findall(EMAIL_REGEX, text):
        token = f"KEEPTOKEN{counter}"
        mapping[token] = match
        text = re.sub(r'\b' + re.escape(match) + r'\b', token, text)
        counter += 1

    for match in re.findall(URL_REGEX, text):
        token = f"KEEPTOKEN{counter}"
        mapping[token] = match
        text = re.sub(re.escape(match), token, text)
        counter += 1

    for match in set(re.findall(ACRONYM_REGEX, text)):
        token = f"KEEPTOKEN{counter}"
        mapping[token] = match
        text = re.sub(r'\b' + re.escape(match) + r'\b', token, text)
        counter += 1

    return text, mapping

def restore_text(text, mapping):
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text

def translate_tamil(text):
    if pd.isna(text):
        return ""
    text = str(text).strip()
    if not text:
        return ""
    protected_text, mapping = protect_text(text)
    try:
        translated = translator.translate(protected_text)
        translated = restore_text(translated, mapping)
        time.sleep(0.15)
        return translated
    except Exception as e:
        print("Translation Error:", e)
        return text

def process_jsonl(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
        for idx, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            body = obj.get("body_cleaned_2", "")
            obj["tamil_body"] = translate_tamil(body)

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            print(f"processed {idx}")

if __name__ == "__main__":
    process_jsonl(INPUT_JSONL, OUTPUT_JSONL)
    print(f"Saved: {OUTPUT_JSONL}")
import pandas as pd
import requests
from tqdm import tqdm

# === CONFIGURATION ===
API_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "mistral-7b-instruct-v0.1"

NLP_INPUT_PATH = "/Users/jaydenai/Desktop/lmstudio/Jayden NLP Data.xlsx"
BPO_INPUT_PATH = "/Users/jaydenai/Desktop/lmstudio/BPO_Notes.xlsx"
OUTPUT_PATH = "/Users/jaydenai/Desktop/evaluated_property_conditions.xlsx"

# === PROMPTS ===
def build_prompt_nlp(desc):
    return f"""[INST]
Classify the condition of this home based on the description provided.

Categories:
- Positive – Only good features are mentioned. No negatives.  
- Negative – Only bad, broken, outdated, or missing features are mentioned. No positives.  
- Mixed Opinion – Includes both good and bad details (e.g., livable but outdated, needs repairs, fair/average condition).  
- No Relevant Information – No physical condition details (e.g., "none," disclaimers, buyer info, comparables, or unrelated remarks).  

Instructions:
- Ignore disclaimers, legal language, buyer information, comparables, or unrelated remarks.  
- Focus only on physical condition details.  
- If multiple areas are described, decide based on the overall impression.  

Output format (always follow exactly):
Category: <Positive | Negative | Mixed Opinion | No Relevant Information>  
Reason: <short explanation, under 40 words>  

Description:
{desc}
[/INST]"""

def build_prompt_bpo(desc):
    return f"""[INST]
Classify the condition of this home description.

Categories:
- Positive – Only good features.
- Negative – Only bad, broken, outdated, or missing features.
- Mixed Opinion – Contains both good and bad condition details (e.g., livable but outdated, could use repairs, fair, average).
- No Relevant Information – No physical condition details. (e.g., "none").

Ignore disclaimers, legal language, buyer information, comparables, or unrelated remarks. Focus only on physical condition details.
If multiple areas are discussed, evaluate the overall impression.

Output format:
Category: <one of the four>
Reason: <under 40 words>

Description:
{desc}
[/INST]"""

# === PARSE MODEL RESPONSE ===
def parse_response(text):
    lines = text.strip().splitlines()
    category = "No Relevant Information"
    reason = "No reason provided."
    for line in lines:
        if line.lower().startswith("category:"):
            category = line.split(":", 1)[1].strip().title()
        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
    return category, reason

# === NLP DATA PROCESSING ===
def process_nlp_data():
    df = pd.read_excel(NLP_INPUT_PATH).iloc[:30, :]
    results = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating NLP Data"):
        result = {
            "Loan Number": row.get("Loan Number", ""),
            "Address": row.get("Address", ""),
            "City": row.get("City", ""),
            "State": row.get("State", ""),
            "Zip": row.get("Zip Code", "")
        }
        for field in ["Kitchen Condition", "Bathrooms Condition", "Interior Appearance Condition"]:
            desc = str(row.get(field, "")).strip()
            if not desc or desc.lower() in ["nan", "none"]:
                result[f"{field} Category"] = "No Relevant Information"
                result[f"{field} Reason"] = "No description provided."
            else:
                prompt = build_prompt_nlp(desc)
                payload = {
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 64
                }
                response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
                reply = response.json()["choices"][0]["message"]["content"].strip()
                category, reason = parse_response(reply)
                result[f"{field} Category"] = category or "Unknown"
                result[f"{field} Reason"] = reason or "No reason provided."
        results.append(result)

    return pd.DataFrame(results)

# === BPO DATA PROCESSING ===
def process_bpo_data():
    df = pd.read_excel(BPO_INPUT_PATH).iloc[:30, :]
    results = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating BPO Notes"):
        fha_case = row.get("FHA Case #", "")
        notes = str(row.get("BPO_NOTES", "")).strip()

        if not notes or notes.lower() in ["nan", "none"]:
            category = "No Relevant Information"
            reason = "No description provided."
        else:
            prompt = build_prompt_bpo(notes)
            payload = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 256
            }
            response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
            reply = response.json()["choices"][0]["message"]["content"].strip()
            category, reason = parse_response(reply)
            category = category or "Unknown"
            reason = reason or "No reason provided."

        results.append({
            "FHA Case #": fha_case,
            "BPO Category": category,
            "BPO Reason": reason
        })

    return pd.DataFrame(results)

# === MERGE RESULTS ===
def merge_results(nlp_df, bpo_df):
    # Temporary normalized key for merging (remove '#' for matching only)
    nlp_df["_match_key"] = nlp_df["Loan Number"].astype(str).str.replace("#", "").str.strip()
    bpo_df["_match_key"] = bpo_df["FHA Case #"].astype(str).str.replace("#", "").str.strip()

    merged = pd.merge(nlp_df, bpo_df, on="_match_key", how="left", suffixes=("", "_BPO"))
    merged.drop(columns=["_match_key"], inplace=True)
    return merged

# === MAIN ===
if __name__ == "__main__":
    nlp_df = process_nlp_data()
    bpo_df = process_bpo_data()
    final_df = merge_results(nlp_df, bpo_df)
    final_df.to_excel(OUTPUT_PATH, index=False)
    print(f"Done! Saved evaluations to {OUTPUT_PATH}")

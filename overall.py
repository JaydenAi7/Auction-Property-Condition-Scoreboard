import pandas as pd
import requests
from tqdm import tqdm

# === CONFIGURATION ===
API_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "mistral-7b-instruct-v0.1"

NLP_INPUT_PATH = "/Users/jaydenai/Desktop/lmstudio/Jayden NLP Data.xlsx"
BPO_INPUT_PATH = "/Users/jaydenai/Desktop/lmstudio/BPO_Notes.xlsx"
OUTPUT_PATH = "/Users/jaydenai/Desktop/evaluated_property_conditions.xlsx"

# === HELPERS ===
def safe_title(val):
    """Convert any value safely to a titled string, handle NaN/float gracefully."""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip().title()

# === PROMPTS ===
def build_prompt_nlp(desc):
    return f"""[INST]
Classify the condition of this home based on the description provided.

Categories:
- Negative – One or more bad, broken, outdated, or missing features are mentioned. No positives.  
- No Relevant Information – No physical condition details (e.g., "none," disclaimers, buyer info, comparables, or unrelated remarks).  
- Mixed Opinion – Includes both good and bad details (e.g., livable but outdated, needs repairs, fair/average condition).  
- Positive – One or more good features are mentioned. No negatives. 

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
- No Relevant Information – No physical condition details (e.g., "none," disclaimers, buyer info, comparables, or unrelated remarks).  
- Negative – One or more bad, broken, outdated, or missing features are mentioned. No positives.  
- Mixed Opinion – Includes both good and bad details (e.g., livable but outdated, needs repairs, fair/average condition).  
- Positive – One or more good features are mentioned. No negatives. 

Ignore disclaimers, legal language, buyer information, comparables, or unrelated remarks. Focus only on physical condition details.
If multiple areas are discussed, evaluate the overall impression.

Output format:
Category: <Positive | Negative | Mixed Opinion | No Relevant Information>
Reason: <short explanation, under 40 words>

Description:
{desc}
[/INST]"""

# === PARSE MODEL RESPONSE ===
def parse_response(text):
    lines = str(text).strip().splitlines()
    category = "No Relevant Information"
    reason = "No reason provided."
    for line in lines:
        if line.lower().startswith("category:"):
            category = safe_title(line.split(":", 1)[1])
        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()
    return category or "No Relevant Information", reason or "No reason provided."

# === OVERALL DECISION FUNCTION ===
def overall_condition(bpo_category, sub_categories):
    """
    Determine overall condition based on BPO category and the 3 sub-categories.
    Args:
        bpo_category (str): Category from BPO
        sub_categories (list[str]): Categories from sub-areas (kitchen, bathrooms, interior)
    Returns:
        str: Overall condition ("Positive", "Negative", "Mixed Opinion", "No Relevant Information", "Flagged")
    """

    # Normalize inputs safely
    bpo = safe_title(bpo_category)
    subs = [safe_title(c) for c in sub_categories]

    # Helper counts
    positives = subs.count("Positive") + subs.count("Slightly Positive")
    negatives = subs.count("Negative")
    mixed = subs.count("Mixed Opinion")
    nori = subs.count("No Relevant Information")
    total = len(subs)

    # === 1. BPO = Positive ===
    if bpo == "Positive":
        if negatives > 0:
            return "Flagged"
        if all(c in ["Positive", "Slightly Positive", "Mixed Opinion", "No Relevant Information"] for c in subs):
            return "Positive"
        return "Mixed Opinion"

    # === 2. BPO = Negative ===
    if bpo == "Negative":
        if positives > 0:
            return "Flagged"
        if all(c in ["Negative", "Mixed Opinion", "No Relevant Information"] for c in subs):
            return "Negative"
        return "Mixed Opinion"

    # === 3. BPO = No Relevant Information ===
    if bpo == "No Relevant Information":
        # Positives
        if positives >= 2 and negatives == 0:
            return "Positive"
        if positives == 1 and (positives + nori == total):
            return "Positive"

        # Negatives
        if negatives >= 2 and positives == 0:
            return "Negative"
        if negatives == 1 and (negatives + nori == total):
            return "Negative"

        # All No Relevant
        if nori == total:
            return "No Relevant Information"

        # Otherwise mixed
        return "Mixed Opinion"

    # === 4. BPO = Mixed Opinion ===
    if bpo == "Mixed Opinion":
        if (positives > 0 and nori > 0) or (negatives > 0 and nori > 0):
            return "Flagged"
        return "Mixed Opinion"

    # Fallback
    return "Mixed Opinion"

# === NLP DATA PROCESSING ===
def process_nlp_data():
    df = pd.read_excel(NLP_INPUT_PATH).iloc[500:550, :]
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
                result[f"{field} Category"] = category
                result[f"{field} Reason"] = reason
        results.append(result)

    return pd.DataFrame(results)

# === BPO DATA PROCESSING ===
def process_bpo_data():
    df = pd.read_excel(BPO_INPUT_PATH).iloc[500:550, :]
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

        results.append({
            "FHA Case #": fha_case,
            "BPO Category": category,
            "BPO Reason": reason
        })

    return pd.DataFrame(results)

# === MERGE RESULTS + OVERALL CONDITION ===
def merge_results(nlp_df, bpo_df):
    nlp_df["_match_key"] = nlp_df["Loan Number"].astype(str).str.replace("#", "").str.strip()
    bpo_df["_match_key"] = bpo_df["FHA Case #"].astype(str).str.replace("#", "").str.strip()

    merged = pd.merge(nlp_df, bpo_df, on="_match_key", how="left", suffixes=("", "_BPO"))
    merged.drop(columns=["_match_key"], inplace=True)

    # Compute overall condition (BPO + subcategories separately)
    merged["Overall Condition"] = merged.apply(lambda row: overall_condition(
        row.get("BPO Category", ""),
        [
            row.get("Kitchen Condition Category", ""),
            row.get("Bathrooms Condition Category", ""),
            row.get("Interior Appearance Condition Category", "")
        ]
    ), axis=1)

    # Move "Overall Condition" before the 3 condition fields
    first_cols = ["Loan Number", "Address", "City", "State", "Zip", "Overall Condition"]
    other_cols = [c for c in merged.columns if c not in first_cols]
    merged = merged[first_cols + other_cols]

    return merged

# === MAIN ===
if __name__ == "__main__":
    nlp_df = process_nlp_data()
    bpo_df = process_bpo_data()
    final_df = merge_results(nlp_df, bpo_df)
    final_df.to_excel(OUTPUT_PATH, index=False)
    print(f"Done! Saved evaluations to {OUTPUT_PATH}")

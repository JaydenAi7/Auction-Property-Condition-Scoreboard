import pandas as pd
import requests
from tqdm import tqdm

# === CONFIGURATION ===
API_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "mistral-7b-instruct-v0.1"
INPUT_PATH = "/Users/jaydenai/Desktop/lmstudio/BPO_Notes.xlsx"
OUTPUT_PATH = "/Users/jaydenai/Desktop/evaluated_property_conditions.xlsx"

# === PROMPT CONSTRUCTION ===
def build_prompt(desc):
    return f"""[INST]
Classify the condition of this home description.

Categories:
- Positive – Only good/functional features.
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

# === MAIN LOGIC ===
def main():
    df = pd.read_excel(INPUT_PATH).iloc[:30, :]  # Adjust limit if needed
    evaluated_rows = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating BPO Notes"):
        fha_case = row.get("FHA Case #", "Unknown")
        notes = str(row.get("BPO_NOTES", "")).strip()

        if not notes or notes.lower() in ["nan", "none"]:
            category = "No Relevant Information"
            reason = "No description provided."
        else:
            prompt = build_prompt(notes)
            payload = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 256
            }
            response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
            reply = response.json()["choices"][0]["message"]["content"].strip()
            category, reason = parse_response(reply)
            if not category:
                category = "Unknown"
            if not reason:
                reason = "No reason provided."

        evaluated_rows.append({
            "FHA Case #": fha_case,
            "Category": category,
            "Reason": reason
        })

    pd.DataFrame(evaluated_rows).to_excel(OUTPUT_PATH, index=False)
    print(f"Done! Saved evaluations to {OUTPUT_PATH}")

# === RUN ===
if __name__ == "__main__":
    main()

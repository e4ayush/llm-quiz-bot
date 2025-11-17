# app/agent.py
import google.generativeai as genai
import re
import json

# --- THIS IS THE "IF/ELSE" LOGIC PROMPT ---
AGENT_PROMPT = """
You are an expert Python code-generation agent. You will be given the text of a quiz and (if necessary) the content of data files.

Your job is to find two things:
1.  The submission URL (e.g., "/submit").
2.  A small, self-contained Python script that, when executed, calculates the final answer.

---
CRITICAL INSTRUCTIONS:
-   **RULE 1: SIMPLE EXTRACTION**
    If the quiz text provides the full JSON to submit (e.g., "... "answer": "some-value" ..."),
    you *MUST* follow EXAMPLE 1. Do not invent a calculation.

-   **RULE 2: COMPLEX CALCULATION**
    *ONLY IF* the answer is not provided (e.g., "sum the file", "find the cutoff"),
    you *MUST* follow EXAMPLE 2 and write a script.

-   **CODE RULES:**
    -   **DO NOT include 'import' statements.** The libraries `io`, `csv`, `re`, `json` are *already imported*.
    -   **DO NOT use 'try...except' blocks.**
    -   **DO NOT use built-in functions like 'next()'.** Use a boolean flag to skip headers.
    -   The script *must* result in a variable named `answer`.
---

You must provide your answer ONLY as a single, valid JSON object in this *exact* format:
{
  "submission_url": "THE_URL_YOU_FOUND",
  "python_script": "THE_PYTHON_CODE_YOU_WROTE"
}

---
EXAMPLE 1 (Obeys RULE 1: Simple Extraction):

Quiz Text:
"Page Content: POST to https://example.com/submit ... { ... "answer": "the-secret-code" }"

Your Response:
{
  "submission_url": "https://example.com/submit",
  "python_script": "answer = 'the-secret-code'"
}

---
EXAMPLE 2 (Obeys RULE 2: Complex Calculation):

Quiz Text:
"Page Content:
CSV file. Cutoff: 42669. POST to /submit-sum
--- Content of file.csv ---
name,amount
apple,20
banana,60000
orange,100000
--- End of file.csv ---"

Your Response:
{
  "submission_url": "/submit-sum",
  "python_script": "data_text = '''name,amount\\napple,20\\nbanana,60000\\norange,100000'''\\ncutoff = 42669\\ntotal = 0\\nis_header = True\\nreader = csv.reader(io.StringIO(data_text))\\nfor row in reader:\\n    if is_header:\\n        is_header = False\\n        continue\\n    if row:\\n        amount = int(row[1])\\n        if amount > cutoff:\\n            total += amount\\nanswer = total"
}
"""

def _extract_json_from_response(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None

async def solve_quiz(api_key: str, final_prompt_text: str) -> dict:
    try:
        genai.configure(api_key=api_key)
        
        # Using the model you selected
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        response = await model.generate_content_async(
            [AGENT_PROMPT, final_prompt_text]
        )
        
        json_string = _extract_json_from_response(response.text)
        
        if not json_string:
            print(f"AI Response was not JSON: {response.text}")
            return {"error": "AI could not find JSON in the text.", "raw_response": response.text}

        return json.loads(json_string)

    except json.JSONDecodeError as e:
        print(f"AI returned invalid JSON: {e}")
        print(f"Raw string from AI: {json_string}")
        return {"error": f"AI returned invalid JSON: {e}", "raw_string": json_string}
    except Exception as e:
        print(f"Error in AI Agent: {e}")
        return {"error": f"AI agent failed: {e}"}
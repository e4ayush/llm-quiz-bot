import sys
import asyncio
import os
import requests
import urllib.parse
import re
import io
import csv
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from app.models import QuizRequest
from app.utils import scrape_quiz_data
from app.agent import solve_quiz

# --- Setup (Same as before) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("FATAL ERROR: GOOGLE_API_KEY environment variable not set.")

app = FastAPI()

# --- NEW: Safe Code Executor with Whitelist ---
def execute_ai_script(script: str):
    """
    Safely executes the Python script from the AI using a whitelisted
    set of built-in functions.
    """
    try:
        # --- THIS IS THE NEW "SAFE" WHITELIST ---
        # We allow basic functions for data processing but nothing
        # that can interact with the file system or network.
        safe_builtins = {
            "int": int,
            "float": float,
            "str": str,
            "len": len,
            "print": print,
            "sum": sum,
            "max": max,
            "min": min,
            "range": range,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "abs": abs,
            "round": round,
        }
        # --- END OF WHITELIST ---
        
        # This is the "scope" where the script will run.
        local_scope = {
            "io": io,
            "csv": csv,
            "re": re,
            "json": json,
            "answer": None # Default value
        }
        
        # We pass our safe_builtins as the *only* built-ins allowed
        exec(script, {"__builtins__": safe_builtins}, local_scope)
        
        # We retrieve the 'answer' variable from the scope
        return local_scope.get('answer', None)

    except Exception as e:
        print(f"---!! ERROR EXECUTING AI SCRIPT !!---")
        print(f"Script: {script}")
        print(f"Error: {e}")
        return {"error": f"Script execution failed: {e}"}

# --- The "Recursive Solver" (Same as before) ---
async def run_quiz_chain(current_url: str, email: str, secret: str):
    try:
        print(f"--- Starting task for: {current_url} ---")
        
        # 1. EYES: Scrape
        print("Scraping the quiz page...")
        scraper_output = await scrape_quiz_data(current_url)
        if "error" in scraper_output:
            print(f"Scraper failed: {scraper_output['error']}")
            return
        quiz_text = scraper_output["text"]
        quiz_html = scraper_output["html"]
        print(f"Scraped content snippet: {quiz_text[:100]}...")

        # 2. TOOL: Fetch data
        supplemental_data = ""
        all_data_links = set(re.findall(r'href=[\'"](\S+?)[\'"]', quiz_html) + 
                           re.findall(r'Scrape (\S+)', quiz_text))
        
        for link in all_data_links:
            is_data_link = (link.endswith(('.csv', '.json', '.txt')) or 
                            '?email=' in link or '?id=' in link or 
                            ('data' in link.lower() and 'email' not in link.lower()))
            
            if is_data_link:
                full_url = urllib.parse.urljoin(current_url, link)
                print(f"Found data link: {full_url}. Fetching its content...")
                data_content = ""
                try:
                    if link.endswith(('.csv', '.json', '.txt')):
                        print("Fetching as raw text file (using requests)...")
                        data_response = requests.get(full_url, timeout=10)
                        data_response.raise_for_status()
                        data_content = data_response.text
                    else:
                        print("Fetching as interactive page (using Playwright)...")
                        data_output = await scrape_quiz_data(full_url)
                        if "error" in data_output: raise Exception(data_output["error"])
                        data_content = data_output["text"]
                    supplemental_data += f"\n\n--- Content of {link} ---\n{data_content}\n--- End of {link} ---"
                except Exception as e:
                    print(f"Failed to fetch data from {full_url}: {e}")
                    continue 

        final_prompt_to_ai = quiz_text + supplemental_data
        
        # 3. BRAIN: Generate Code
        print("Sending content (quiz + data) to AI agent to generate code...")
        agent_task = await solve_quiz(API_KEY, final_prompt_to_ai)
        
        if "error" in agent_task:
            print(f"Agent failed: {agent_task['error']}")
            return

        submission_url_from_ai = agent_task.get("submission_url")
        python_script = agent_task.get("python_script") 

        if not submission_url_from_ai or not python_script:
            print("Agent did not return expected URL or script.")
            return

        # 4. ACTION: Execute Code & Submit
        print("Executing AI-generated script...")
        calculated_answer = execute_ai_script(python_script) # This now uses the safe whitelist

        if calculated_answer is None or isinstance(calculated_answer, dict) and 'error' in calculated_answer:
            print(f"AI script failed. Answer: {calculated_answer}")
            return

        print(f"Script executed. Calculated answer: {calculated_answer}")
        
        submission_url = urllib.parse.urljoin(current_url, submission_url_from_ai)
        payload = {
            "email": email,
            "secret": secret,
            "url": current_url,
            "answer": calculated_answer 
        }
        
        print(f"Submitting to: {submission_url}")
        response = requests.post(submission_url, json=payload)
        
        response_data = {}
        try:
            if response.status_code >= 400:
                print(f"Submission failed. Server gave HTTP {response.status_code}.")
                print(f"Server response text: {response.text[:150]}...")
                return 
            response_data = response.json()
            print(f"Submission successful. Response: {response_data}")
        except requests.exceptions.JSONDecodeError:
            print(f"Submission was OK (Status {response.status_code}), but server response was NOT JSON.")
            print(f"Server response text: {response.text[:150]}...")
            return

        # 5. RECURSION: Check for new URL
        new_url = response_data.get("url")
        if new_url:
            next_url_full = urllib.parse.urljoin(submission_url, new_url)
            print(f"New URL found! Starting next task: {next_url_full}")
            await run_quiz_chain(next_url_full, email, secret)
        else:
            print("--- Quiz chain complete! ---")
            
    except Exception as e:
        print(f"--- FATAL ERROR in chain for {current_url}: {e} ---")

# --- Webhook Endpoint (Same as before) ---
@app.post("/webhook")
async def handle_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    if not API_KEY:
        return {"error": "Server is missing its API key."}
        
    print(f"Received job for: {request.url}. Handing off to background task.")
    
    background_tasks.add_task(
        run_quiz_chain,
        current_url=str(request.url),
        email=request.email,
        secret=request.secret
    )
    
    return {"message": "Task received, processing in background."}

@app.get("/")
async def root():
    return {"message": "Quiz Bot is running!"}

# --- Run the server (Same as before) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
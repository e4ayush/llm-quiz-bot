import google.generativeai as genai
import os

try:
    # 1. Get your key from the environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set it in your terminal before running this script:")
        print('$env:GOOGLE_API_KEY = "YOUR_API_KEY"')
        exit()

    genai.configure(api_key=api_key)

    print("Fetching available models for your API key...")
    print("---------------------------------------------")

    # 2. Loop through and find all usable models
    for m in genai.list_models():
        # 'generateContent' is the method we need
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

    print("---------------------------------------------")
    print("Done. Pick one of these models for your agent.py file.")

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure your API key is correct and has 'Generative Language API' enabled in AI Studio.")
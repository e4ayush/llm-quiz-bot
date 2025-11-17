import requests

# The URL provided in the prompt
url = "https://tds-llm-analysis.s-anand.net/submit"

# The data payload
data = {
    "email": "your email",            # Replace with your actual email
    "secret": "your secret",          # Replace with your actual secret
    "url": "https://tds-llm-analysis.s-anand.net/demo",
    "answer": "anything you want"     # Replace if you have a specific answer
}

try:
    print(f"Submitting to {url}...")
    response = requests.post(url, json=data)
    
    # Check if the request was successful
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(response.json())

except Exception as e:
    print(f"An error occurred: {e}")
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('CLAUDE_API_KEY')
if api_key:
    print("API key found")
else:
    print("No API key found")

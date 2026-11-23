
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

try:
    composio = Composio()
    result = composio.client.tools.list()

    print("SUCCESS: Connected to Composio!")
    print("API authentication is working.")
    print("Response received from Composio.")

except Exception as e:
    print("Connection failed.")
    print(type(e).__name__, str(e))

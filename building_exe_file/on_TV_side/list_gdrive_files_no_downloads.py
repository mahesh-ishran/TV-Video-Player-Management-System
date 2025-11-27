import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

# Get API key from environment variable
API_KEY = os.getenv('GDRIVE_API_KEY')
if not API_KEY:
    raise ValueError("GDRIVE_API_KEY environment variable not set")

folder_id = "........................"

try:
    service = build('drive', 'v3', developerKey=API_KEY)

    # List files in the folder
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType, size, createdTime)"
    ).execute()

    files = results.get('files', [])
except HttpError as error:
    print(f"An error occurred: {error}")
    files = []
except Exception as error:
    print(f"An unexpected error occurred: {error}")
    files = []

if files:
    print(f"Found {len(files)} files:\\n")
    for idx, file in enumerate(files, 1):
        print(f"{idx}. {file['name']}")
        print(f"   ID: {file['id']}")
        print(f"   Type: {file.get('mimeType', 'Unknown')}")
        print(f"   Size: {file.get('size', 'N/A')} bytes")
        print()
else:
    print("No files found.")

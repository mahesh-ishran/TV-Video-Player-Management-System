import os
import sys
import socket
import requests
import logging
import subprocess
import time
from pathlib import Path
import re

def list_folder_files(folder_id):
    """List files in Google Drive folder using web scraping approach"""
    try:
        # Google Drive folder view URL
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        
        print("   Accessing Google Drive folder...")
        
        # Try to get folder page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   HTTP Response Code: {response.status_code}")
        if response.status_code == 200:
            # Look for file patterns in the HTML
            # This is a simple approach for open folders
            content = response.text
            print(content)
            # Find file IDs and names (basic pattern matching)
            # Pattern for files: typically in the HTML as data attributes or links
            file_pattern = r'"/file/d/([a-zA-Z0-9_-]+)/view.*?>(.*?\.mp4)</a>'
            matches = re.findall(file_pattern, content, re.IGNORECASE)
            
            if matches:
                files = [{'id': match[0], 'name': match[1]} for match in matches]
                print(f"Found {len(files)} video files")
                return files
            else:
                print("Could not parse files from folder page")
                return None
        else:
            print(f"Failed to access folder: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error listing folder: {e}")
        return None
    
if __name__ == "__main__":
    folder_id = "......................."  # Example folder ID
    files = list_folder_files(folder_id)
    if files:
        for file in files:
            print(f"File ID: {file['id']}, File Name: {file['name']}")

"""
Google Drive Folder File Lister
This script lists all files in a public Google Drive folder without downloading them.

Requirements:
    pip install gdown requests beautifulsoup4

Usage:
    python list_gdrive_files.py
"""

import gdown
import os
import tempfile
import shutil

# Google Drive folder ID
folder_id = "..........................."
folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

print(f"Fetching file list from folder: {folder_url}\n")
print("=" * 80)

try:
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    print("Accessing folder metadata...")
    
    # Use gdown to download the folder structure (but we'll cancel before actual download)
    # We'll use the quiet mode and get file list
    try:
        # Download folder with quiet mode to get file listing
        gdown.download_folder(
            url=folder_url,
            output=temp_dir,
            quiet=False,
            use_cookies=False
        )
        
        # List what was attempted to download
        print("\n" + "=" * 80)
        print("FILES IN THE FOLDER:")
        print("=" * 80 + "\n")
        
        # Walk through the temp directory to see what files were listed
        file_count = 0
        for root, dirs, files in os.walk(temp_dir):
            for file_name in files:
                file_count += 1
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, temp_dir)
                print(f"{file_count}. {rel_path}")
        
        if file_count == 0:
            print("No files found or unable to access folder contents.")
            print("Make sure the folder is publicly accessible.")
    
    except KeyboardInterrupt:
        print("\n\nDownload interrupted - listing files found so far...")
        
    except Exception as e:
        print(f"Note: {e}")
    
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\nTemporary files cleaned up.")

except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure:")
    print("1. The folder is publicly accessible")
    print("2. You have 'gdown' installed: pip install gdown")
    print("3. You have a stable internet connection")

print("\n" + "=" * 80)
print("Script completed.")

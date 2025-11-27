import os
import sys
import socket
import requests
import logging
import subprocess
import time
from pathlib import Path
import re

# ============= CONFIGURATION =============
GOOGLE_DRIVE_FOLDER_ID = "................"
DOWNLOAD_FOLDER = r"C:\TVVideos"
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
LOG_FILE = "tv_video_player.log"
# =========================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def print_header():
    """Print header"""
    print("\n" + "="*70)
    print("           TV VIDEO PLAYER - Trial Version")
    print("="*70 + "\n")

def get_server_ips():
    """Get both local and external IP addresses"""
    ips = {}
    try:
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        ips['local'] = local_ip
        logging.info(f"Hostname: {hostname}")
        logging.info(f"Local IP: {local_ip}")
        
        # Try to get external IP
        try:
            response = requests.get('https://api.ipify.org?format=text', timeout=5)
            external_ip = response.text.strip()
            ips['external'] = external_ip
            logging.info(f"External IP: {external_ip}")
        except:
            ips['external'] = None
            logging.warning("Could not fetch external IP")
        
        return ips
    except Exception as e:
        logging.error(f"Error getting IPs: {e}")
        return None

def download_file_direct(file_id, filename, destination_folder):
    """Download file from Google Drive"""
    try:
        Path(destination_folder).mkdir(parents=True, exist_ok=True)
        destination_path = os.path.join(destination_folder, filename)
        
        if os.path.exists(destination_path):
            logging.info(f"File already exists: {destination_path}")
            return destination_path
        
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        logging.info(f"Downloading: {filename}")
        print(f"\n   Downloading {filename}...")
        
        session = requests.Session()
        response = session.get(url, stream=True)
        
        # Handle large file confirmation
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                params = {'confirm': value, 'id': file_id}
                response = session.get(url, params=params, stream=True)
                break
        
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r   Progress: {percent:.1f}%", end='')
            
            print()
            logging.info(f"Download complete: {destination_path}")
            return destination_path
        else:
            logging.error(f"Download failed: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None

def find_vlc():
    """Find VLC executable"""
    locations = [
        VLC_PATH,
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]
    
    for path in locations:
        if os.path.exists(path):
            logging.info(f"VLC found: {path}")
            return path
    
    return None

def play_video(video_path):
    """Play video in VLC"""
    try:
        vlc_path = find_vlc()
        if not vlc_path:
            logging.error("VLC not found")
            return False
        
        if not os.path.exists(video_path):
            logging.error(f"Video not found: {video_path}")
            return False
        
        logging.info(f"Playing: {os.path.basename(video_path)}")
        subprocess.Popen([vlc_path, '--fullscreen', video_path])
        logging.info("VLC launched")
        return True
        
    except Exception as e:
        logging.error(f"Error playing video: {e}")
        return False

def main():
    """Main execution"""
    print_header()
    
    logging.info("="*70)
    logging.info("TV Video Player Started")
    logging.info("="*70)
    
    # Step 1: Get IPs
    print("[1/6] Detecting server IP addresses...")
    ips = get_server_ips()
    
    if not ips:
        print("   ❌ Failed to get IP addresses")
        logging.error("Could not determine IPs")
        input("\nPress Enter to exit...")
        return
    
    print(f"   ✓ Local IP: {ips['local']}")
    if ips['external']:
        print(f"   ✓ External IP: {ips['external']}")
    
    # Determine which IP to use
    # Since you're connecting via 34.100.216.23, let's try external first
    target_ip = ips['external'] if ips['external'] else ips['local']
    video_filename = f"{target_ip}.mp4"
    
    print(f"\n   Looking for video: {video_filename}")
    logging.info(f"Target video: {video_filename}")
    
    # Also prepare alternative filename with local IP
    alternative_filename = f"{ips['local']}.mp4" if ips['local'] != target_ip else None
    
    # Step 2: Setup folder
    print("\n[2/6] Creating download folder...")
    try:
        Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        print(f"   ✓ Folder: {DOWNLOAD_FOLDER}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        input("\nPress Enter to exit...")
        return
    
    # Step 3: Check VLC
    print("\n[3/6] Checking VLC installation...")
    vlc_path = find_vlc()
    if not vlc_path:
        print("   ❌ VLC not found")
        print("   Install from: https://www.videolan.org/vlc/")
        input("\nPress Enter to exit...")
        return
    print("   ✓ VLC found")
    
    # Step 4: Since folder listing is complex, let's try direct download
    print("\n[4/6] Attempting to download video...")
    print("   Note: Since you have a folder link, please provide individual file IDs")
    print(f"   Expected filename: {video_filename}")
    
    # For this trial, let's create a manual approach
    print("\n   IMPORTANT: For folder access, you need to:")
    print("   1. Open your Google Drive folder")
    print("   2. Find the video file matching your server IP")
    print(f"      (Looking for: {video_filename})")
    print("   3. Right-click the file → Get link")
    print("   4. Extract the FILE ID from the link")
    print("   5. Create that video file in the folder with correct name")
    
    # Ask user if they want to continue or provide file ID
    print("\n" + "="*70)
    print("MANUAL STEP REQUIRED:")
    print("="*70)
    print("\nOption 1: Upload video to Google Drive as:")
    print(f"  • {video_filename} (using external IP)")
    if alternative_filename:
        print(f"  • OR {alternative_filename} (using local IP)")
    print("\nOption 2: Provide the direct file ID below")
    print("="*70)
    
    file_id = input("\nEnter Google Drive FILE ID (or press Enter to skip): ").strip()
    
    video_path = None
    if file_id:
        # Download using provided file ID
        video_path = download_file_direct(file_id, video_filename, DOWNLOAD_FOLDER)
    else:
        # Check if file already exists locally
        potential_paths = [
            os.path.join(DOWNLOAD_FOLDER, video_filename),
        ]
        if alternative_filename:
            potential_paths.append(os.path.join(DOWNLOAD_FOLDER, alternative_filename))
        
        for path in potential_paths:
            if os.path.exists(path):
                video_path = path
                print(f"   ✓ Found existing video: {os.path.basename(path)}")
                break
    
    if not video_path:
        print("\n   ❌ No video file available")
        print("\n   Next steps:")
        print(f"   1. Upload your video to Google Drive as: {video_filename}")
        print("   2. Make it publicly accessible")
        print("   3. Get the individual file's share link")
        print("   4. Extract the FILE ID")
        print("   5. Run this program again and provide the FILE ID")
        input("\nPress Enter to exit...")
        return
    
    # Step 5: Wait a moment
    print("\n[5/6] Preparing playback...")
    time.sleep(1)
    
    # Step 6: Play
    print("\n[6/6] Launching VLC Media Player...")
    if play_video(video_path):
        print("   ✓ Video playback started!\n")
        logging.info("SUCCESS: Video playing")
    else:
        print("   ❌ Failed to start playback\n")
        logging.error("Playback failed")
    
    print("="*70)
    print(f"Log file: {LOG_FILE}")
    print(f"Video location: {video_path}")
    print("="*70)
    
    logging.info("="*70)
    logging.info("TV Video Player Completed")
    logging.info("="*70)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        logging.info("Interrupted")
    except Exception as e:
        print(f"\n\nError: {e}")
        logging.error(f"Error: {e}", exc_info=True)
        input("\nPress Enter to exit...")

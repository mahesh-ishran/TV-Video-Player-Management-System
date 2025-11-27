import os
import sys
import socket
import requests
import logging
import json
import subprocess
import time
from pathlib import Path

def load_config():
    """Load configuration from config.json"""
    config_file = "config.json"
    default_config = {
        "google_drive_file_id": "",
        "download_folder": r"C:\TV_Videos",
        "vlc_path": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "log_file": "tv_video_player.log",
        "fullscreen_mode": True,
        "auto_close_after_seconds": 0
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default configuration file: {config_file}")
            print("Please edit config.json and add your Google Drive file ID")
            return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

# Load configuration
CONFIG = load_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['log_file']),
        logging.StreamHandler(sys.stdout)
    ]
)

def print_header():
    """Print application header"""
    header = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           TV VIDEO PLAYER - Configuration Version       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(header)

def get_server_ip():
    """Get the server's IP address"""
    try:
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logging.info(f"Hostname: {hostname}")
        logging.info(f"Local IP (from hostname): {local_ip}")
        print(f"   Local IP: {local_ip}")
        
        # Try to get external IP as well
        try:
            response = requests.get('https://api.ipify.org?format=text', timeout=5)
            external_ip = response.text.strip()
            logging.info(f"External IP (public): {external_ip}")
            print(f"   External IP: {external_ip}")
        except:
            external_ip = None
            logging.warning("Could not fetch external IP")
        
        # For this trial, we'll use the local IP by default
        # But log both for user to see
        return local_ip
        
    except Exception as e:
        logging.error(f"Error getting server IP: {e}")
        return None

def download_from_google_drive(file_id, destination_path):
    """Download file from Google Drive"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        logging.info(f"Downloading file ID: {file_id}")
        print(f"\n📥 Downloading from Google Drive...")
        
        session = requests.Session()
        response = session.get(url, stream=True)
        
        # Handle virus scan warning for large files
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
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            print(f"\r   Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
            
            print()  # New line
            logging.info(f"Download complete: {os.path.basename(destination_path)}")
            logging.info(f"Size: {downloaded / (1024*1024):.2f} MB")
            return True
        else:
            logging.error(f"Download failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"Download error: {e}")
        return False

def setup_download_folder(folder_path):
    """Create download folder if needed"""
    try:
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        logging.info(f"Download folder ready: {folder_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating folder: {e}")
        return False

def find_vlc():
    """Find VLC executable"""
    vlc_locations = [
        CONFIG['vlc_path'],
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files\VLC\vlc.exe",
    ]
    
    for path in vlc_locations:
        if os.path.exists(path):
            logging.info(f"VLC found: {path}")
            return path
    
    logging.error("VLC not found in any standard location")
    return None

def play_video(video_path, fullscreen=True):
    """Launch VLC to play video"""
    try:
        vlc_path = find_vlc()
        if not vlc_path:
            return False
        
        if not os.path.exists(video_path):
            logging.error(f"Video not found: {video_path}")
            return False
        
        logging.info(f"Playing: {os.path.basename(video_path)}")
        
        # Build VLC command
        cmd = [vlc_path]
        if fullscreen:
            cmd.append('--fullscreen')
        cmd.append(video_path)
        
        subprocess.Popen(cmd)
        logging.info("VLC launched successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error playing video: {e}")
        return False

def validate_config():
    """Validate configuration"""
    issues = []
    
    if not CONFIG['google_drive_file_id'] or CONFIG['google_drive_file_id'] == "YOUR_FILE_ID_HERE":
        issues.append("Google Drive File ID not configured")
    
    return issues

def main():
    """Main execution"""
    print_header()
    
    logging.info("="*60)
    logging.info("TV Video Player Started")
    logging.info("="*60)
    
    # Validate configuration
    config_issues = validate_config()
    if config_issues:
        print("\n❌ Configuration Issues:")
        for issue in config_issues:
            print(f"   - {issue}")
        print(f"\nPlease edit 'config.json' and fix these issues.")
        logging.error("Configuration validation failed")
        input("\nPress Enter to exit...")
        return
    
    print("✅ Configuration valid\n")
    
    # Step 1: Get IP
    print("[1/5] Getting server IP address...")
    server_ip = get_server_ip()
    if not server_ip:
        print("❌ Failed to get IP address")
        input("\nPress Enter to exit...")
        return
    print(f"   ✓ Server IP: {server_ip}\n")
    
    # Step 2: Setup folder
    print("[2/5] Setting up download folder...")
    if not setup_download_folder(CONFIG['download_folder']):
        print("❌ Failed to create download folder")
        input("\nPress Enter to exit...")
        return
    print(f"   ✓ Folder: {CONFIG['download_folder']}\n")
    
    # Step 3: Check VLC
    print("[3/5] Checking VLC Media Player...")
    vlc_path = find_vlc()
    if not vlc_path:
        print("❌ VLC not found")
        print("   Please install VLC from https://www.videolan.org/vlc/")
        input("\nPress Enter to exit...")
        return
    print(f"   ✓ VLC found\n")
    
    # Step 4: Determine video name and download
    video_filename = f"{server_ip}.mp4"
    video_path = os.path.join(CONFIG['download_folder'], video_filename)
    
    print(f"[4/5] Processing video: {video_filename}")
    
    if os.path.exists(video_path):
        print(f"   ✓ Video already exists (skipping download)\n")
        logging.info(f"Using existing video: {video_path}")
    else:
        if not download_from_google_drive(CONFIG['google_drive_file_id'], video_path):
            print("\n❌ Download failed")
            print("\nPlease check:")
            print("   - File ID is correct in config.json")
            print("   - File is publicly accessible on Google Drive")
            print("   - Internet connection is working")
            input("\nPress Enter to exit...")
            return
        print("   ✓ Download successful\n")
    
    # Brief pause to ensure file is ready
    time.sleep(1)
    
    # Step 5: Play video
    print("[5/5] Launching video player...")
    if play_video(video_path, CONFIG['fullscreen_mode']):
        print("   ✓ Video playback started!\n")
        logging.info("SUCCESS: Video is now playing")
    else:
        print("   ❌ Failed to start playback\n")
        logging.error("Failed to play video")
    
    # Auto-close if configured
    if CONFIG['auto_close_after_seconds'] > 0:
        print(f"Closing in {CONFIG['auto_close_after_seconds']} seconds...")
        time.sleep(CONFIG['auto_close_after_seconds'])
    else:
        print("="*60)
        print(f"Log file: {CONFIG['log_file']}")
        print(f"Video location: {video_path}")
        print("="*60)
        input("\nPress Enter to exit...")
    
    logging.info("="*60)
    logging.info("TV Video Player Completed")
    logging.info("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        logging.info("Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}", exc_info=True)
        input("\nPress Enter to exit...")

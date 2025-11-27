import os
import sys
import socket
import requests
import logging
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import threading

# ============= CONFIGURATION =============
GOOGLE_DRIVE_API_KEY = "............................."
GOOGLE_DRIVE_FOLDER_ID = "............................"
DOWNLOAD_FOLDER = r"C:\TVVideos"
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
LOG_FILE = "tv_video_player.log"

# Monitoring settings
CHECK_INTERVAL_SECONDS = 60  # Check for new videos every 5 minutes
INFINITE_LOOP = True  # Play video in infinite loop
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

class TVVideoPlayer:
    def __init__(self):
        self.server_ip = None
        self.current_video_path = None
        self.current_video_id = None
        self.vlc_process = None
        self.monitoring = True
        
    def print_header(self):
        """Print application header"""
        header = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║           TV VIDEO PLAYER - Advanced Auto-Monitor                ║
║                   Infinite Loop Playback                         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
        print(header)
        logging.info("="*70)
        logging.info("TV Video Player - Advanced Auto-Monitor Started")
        logging.info("="*70)
    
    def get_server_ip(self):
        """Get the server's IP address"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logging.info(f"Hostname: {hostname}")
            logging.info(f"Local IP: {local_ip}")
            
            # Try to get external IP as well
            try:
                response = requests.get('https://api.ipify.org?format=text', timeout=5)
                external_ip = response.text.strip()
                logging.info(f"External IP: {external_ip}")
                print(f"   Local IP: {local_ip}")
                print(f"   External IP: {external_ip}")
            except:
                logging.warning("Could not fetch external IP")
                print(f"   Local IP: {local_ip}")
            
            self.server_ip = external_ip
            return external_ip
            
        except Exception as e:
            logging.error(f"Error getting server IP: {e}")
            return None
    
    def list_drive_files(self):
        """List all files in Google Drive folder using API"""
        try:
            url = "https://www.googleapis.com/drive/v3/files"
            params = {
                'q': f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false and mimeType contains 'video/'",
                'fields': 'files(id, name, createdTime, modifiedTime, size)',
                'key': GOOGLE_DRIVE_API_KEY,
                'orderBy': 'createdTime desc'
            }
            
            logging.info("Querying Google Drive folder...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('files', [])
                logging.info(f"Found {len(files)} video files in folder")
                return files
            elif response.status_code == 403:
                logging.error("API Key authentication failed. Check your API key.")
                print("   ❌ Invalid API Key! Please check your configuration.")
                return None
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            return None
    
    def find_latest_video_for_ip(self, files):
        """Find the latest video file matching server IP"""
        if not files:
            return None
        
        # Look for files matching IP patterns
        ip_patterns = [
            f"{self.server_ip}.mp4",
            f"{self.server_ip}.MP4",
            f"{self.server_ip}.avi",
            f"{self.server_ip}.mkv",
        ]
        
        matching_files = []
        for file in files:
            for pattern in ip_patterns:
                if file['name'] == pattern or file['name'].startswith(self.server_ip):
                    matching_files.append(file)
                    break
        
        if not matching_files:
            logging.warning(f"No video found matching IP: {self.server_ip}")
            return None
        
        # Sort by creation time (already sorted by API, but double-check)
        matching_files.sort(key=lambda x: x.get('createdTime', ''), reverse=True)
        
        latest_file = matching_files[0]
        logging.info(f"Latest video: {latest_file['name']} (Created: {latest_file.get('createdTime', 'N/A')})")
        
        return latest_file
    
    def download_video(self, file_info):
        """Download video from Google Drive"""
        try:
            file_id = file_info['id']
            filename = file_info['name']
            
            # Create download folder
            Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
            destination_path = os.path.join(DOWNLOAD_FOLDER, filename)
            
            # Check if already downloaded and same file
            if os.path.exists(destination_path) and self.current_video_id == file_id:
                logging.info(f"Video already downloaded: {filename}")
                return destination_path
            
            # Download using Drive API
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_DRIVE_API_KEY}"
            
            logging.info(f"Downloading: {filename}")
            print(f"\n   📥 Downloading {filename}...")
            
            response = requests.get(url, stream=True, timeout=30)
            
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
                logging.info(f"Size: {downloaded / (1024*1024):.2f} MB")
                
                self.current_video_id = file_id
                return destination_path
            else:
                logging.error(f"Download failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Download error: {e}")
            return None
    
    def find_vlc(self):
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
        
        logging.error("VLC not found")
        return None
    
    def play_video_loop(self, video_path):
        """Play video in infinite loop using VLC"""
        try:
            vlc_path = self.find_vlc()
            if not vlc_path:
                return False
            
            if not os.path.exists(video_path):
                logging.error(f"Video not found: {video_path}")
                return False
            
            # Stop existing VLC process if running
            self.stop_playback()
            
            logging.info(f"Starting playback: {os.path.basename(video_path)}")
            print(f"   🎬 Playing: {os.path.basename(video_path)}")
            
            # VLC command with infinite loop
            cmd = [
                vlc_path,
                '--fullscreen',
                '--loop',  # Infinite loop
                '--no-video-title-show',  # Don't show filename on video
                '--no-osd',  # No on-screen display
                video_path
            ]
            
            self.vlc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logging.info("VLC launched in infinite loop mode")
            self.current_video_path = video_path
            return True
            
        except Exception as e:
            logging.error(f"Error playing video: {e}")
            return False
    
    def stop_playback(self):
        """Stop current VLC playback"""
        try:
            if self.vlc_process and self.vlc_process.poll() is None:
                logging.info("Stopping current playback...")
                self.vlc_process.terminate()
                time.sleep(1)
                if self.vlc_process.poll() is None:
                    self.vlc_process.kill()
                logging.info("Playback stopped")
        except Exception as e:
            logging.error(f"Error stopping playback: {e}")
    
    def is_vlc_running(self):
        """Check if VLC is still running"""
        if self.vlc_process:
            return self.vlc_process.poll() is None
        return False
    
    def monitor_and_update(self):
        """Monitor folder for new videos and update if found"""
        logging.info(f"Starting monitoring (checking every {CHECK_INTERVAL_SECONDS} seconds)")
        print(f"\n   🔄 Monitoring for updates every {CHECK_INTERVAL_SECONDS//60} minutes...")
        
        while self.monitoring:
            try:
                time.sleep(CHECK_INTERVAL_SECONDS)
                
                logging.info("Checking for video updates...")
                print(f"\n   🔍 Checking for new videos... ({datetime.now().strftime('%H:%M:%S')})")
                
                # List files
                files = self.list_drive_files()
                if not files:
                    continue
                
                # Find latest video
                latest_video = self.find_latest_video_for_ip(files)
                if not latest_video:
                    continue
                
                # Check if it's a new video
                if latest_video['id'] != self.current_video_id:
                    logging.info(f"New video detected: {latest_video['name']}")
                    print(f"   🆕 New video found! Updating...")
                    
                    # Download new video
                    video_path = self.download_video(latest_video)
                    if video_path:
                        # Play new video
                        self.play_video_loop(video_path)
                        print(f"   ✅ Now playing updated video")
                else:
                    logging.info("No new video updates")
                    print(f"   ✓ No updates (current video is latest)")
                
                # Check if VLC crashed and restart if needed
                if not self.is_vlc_running() and self.current_video_path:
                    logging.warning("VLC not running, restarting playback...")
                    print(f"   ⚠️  Restarting playback...")
                    self.play_video_loop(self.current_video_path)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        print("\n[1/5] Getting server IP address...")
        if not self.get_server_ip():
            print("   ❌ Failed to get IP address")
            input("\nPress Enter to exit...")
            return
        print(f"   ✓ Server IP: {self.server_ip}")
        
        print("\n[2/5] Setting up folders...")
        try:
            Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Download folder: {DOWNLOAD_FOLDER}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            input("\nPress Enter to exit...")
            return
        
        print("\n[3/5] Checking VLC installation...")
        if not self.find_vlc():
            print("   ❌ VLC not found")
            input("\nPress Enter to exit...")
            return
        print("   ✓ VLC found")
        
        print("\n[4/5] Connecting to Google Drive...")
        files = self.list_drive_files()
        if files is None:
            print("   ❌ Failed to access Google Drive")
            print("   Please check your API key")
            input("\nPress Enter to exit...")
            return
        
        print(f"   ✓ Connected - {len(files)} video files found")
        
        latest_video = self.find_latest_video_for_ip(files)
        if not latest_video:
            print(f"   ❌ No video found for IP: {self.server_ip}")
            print(f"\n   Please upload a video named: {self.server_ip}.mp4")
            input("\nPress Enter to exit...")
            return
        
        print(f"   ✓ Found video: {latest_video['name']}")
        
        print("\n[5/5] Downloading and starting playback...")
        video_path = self.download_video(latest_video)
        if not video_path:
            print("   ❌ Download failed")
            input("\nPress Enter to exit...")
            return
        
        if not self.play_video_loop(video_path):
            print("   ❌ Failed to start playback")
            input("\nPress Enter to exit...")
            return
        
        print("   ✓ Playback started in infinite loop!")
        
        print("\n" + "="*70)
        print("STATUS: Video is now playing in infinite loop")
        print(f"Monitoring for updates every {CHECK_INTERVAL_SECONDS//60} minutes")
        print("Press Ctrl+C to stop")
        print("="*70)
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=self.monitor_and_update, daemon=True)
        monitor_thread.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping...")
            self.monitoring = False
            self.stop_playback()
            logging.info("Application stopped by user")
            print("Goodbye!")

def main():
    """Entry point"""
    player = TVVideoPlayer()
    player.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n\nUnexpected error: {e}")
        input("\nPress Enter to exit...")

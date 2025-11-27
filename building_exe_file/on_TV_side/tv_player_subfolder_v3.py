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

def load_config():
    """Load configuration from JSON file"""
    config_file = "tv_player_subfolder_v3_config.json"
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        print("Please ensure tv_player_subfolder_v3_config.json is in the same folder as this script.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required = ['google_drive_api_key', 'main_folder_id']
        for field in required:
            if not config.get(field) or "YOUR_" in config[field].upper():
                print(f"❌ Configuration error: {field} not set")
                print(f"Please edit {config_file} and add your {field}")
                input("\nPress Enter to exit...")
                sys.exit(1)
        
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing configuration file: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

# Load configuration
CONFIG = load_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG.get('log_file', 'tv_video_player.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

class TVVideoPlayer:
    def __init__(self):
        self.config = CONFIG
        self.external_ip = None
        self.subfolder_id = None
        self.current_video_path = None
        self.current_video_id = None
        self.current_video_name = None
        self.vlc_process = None
        self.monitoring = True
        self.transition_lock = threading.Lock()
        
    def print_header(self):
        """Print application header"""
        header = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        TV VIDEO PLAYER - Subfolder Auto-Monitor System          ║
║              Infinite Loop with Smooth Transitions              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
        print(header)
        logging.info("="*70)
        logging.info("TV Video Player - Subfolder-Based Started")
        logging.info("="*70)
    
    def get_external_ip(self):
        """Get the server's external IP address"""
        try:
            # Get local IP for reference
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logging.info(f"Hostname: {hostname}")
            logging.info(f"Local IP: {local_ip}")
            print(f"   Local IP: {local_ip}")
            
            # Get external IP (this is what we'll use for subfolder matching)
            logging.info("Fetching external IP address...")
            response = requests.get('https://api.ipify.org?format=text', timeout=10)
            external_ip = response.text.strip()
            
            logging.info(f"External IP: {external_ip}")
            print(f"   External IP: {external_ip}")
            
            self.external_ip = external_ip
            return external_ip
            
        except Exception as e:
            logging.error(f"Error getting external IP: {e}")
            print(f"   ⚠️  Could not get external IP, trying alternative methods...")
            
            # Fallback to other IP check services
            fallback_services = [
                'https://ifconfig.me/ip',
                'https://icanhazip.com',
                'https://checkip.amazonaws.com'
            ]
            
            for service in fallback_services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        external_ip = response.text.strip()
                        logging.info(f"External IP (from {service}): {external_ip}")
                        print(f"   External IP: {external_ip}")
                        self.external_ip = external_ip
                        return external_ip
                except:
                    continue
            
            logging.error("Could not determine external IP from any source")
            return None
    
    def list_subfolders(self):
        """List all subfolders in main folder"""
        try:
            url = "https://www.googleapis.com/drive/v3/files"
            params = {
                'q': f"'{self.config['main_folder_id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                'fields': 'files(id, name)',
                'key': self.config['google_drive_api_key']
            }
            
            logging.info("Listing subfolders in main folder...")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                folders = data.get('files', [])
                logging.info(f"Found {len(folders)} subfolders")
                
                for folder in folders:
                    logging.debug(f"  Subfolder: {folder['name']} (ID: {folder['id']})")
                
                return folders
            elif response.status_code == 403:
                logging.error("API Key authentication failed")
                return None
            else:
                logging.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error listing subfolders: {e}")
            return None
    
    def find_my_subfolder(self, subfolders):
        """Find subfolder matching this TV's external IP"""
        if not subfolders:
            return None
        
        # Look for exact match or partial match
        for folder in subfolders:
            folder_name = folder['name'].strip()
            
            # Exact match
            if folder_name == self.external_ip:
                logging.info(f"Found exact match subfolder: {folder_name}")
                return folder
            
            # Partial match (folder name contains IP)
            if self.external_ip in folder_name:
                logging.info(f"Found partial match subfolder: {folder_name}")
                return folder
            
            # IP contains folder name (reverse check)
            if folder_name in self.external_ip:
                logging.info(f"Found reverse match subfolder: {folder_name}")
                return folder
        
        logging.warning(f"No subfolder found matching IP: {self.external_ip}")
        logging.info(f"Available subfolders: {[f['name'] for f in subfolders]}")
        return None
    
    def list_videos_in_subfolder(self, subfolder_id):
        """List all video files in the TV's subfolder"""
        try:
            url = "https://www.googleapis.com/drive/v3/files"
            params = {
                'q': f"'{subfolder_id}' in parents and trashed=false and (mimeType contains 'video/' or name contains '.mp4' or name contains '.avi' or name contains '.mkv')",
                'fields': 'files(id, name, createdTime, modifiedTime, size, mimeType)',
                'key': self.config['google_drive_api_key'],
                'orderBy': 'createdTime desc'
            }
            
            logging.info(f"Listing videos in subfolder...")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('files', [])
                logging.info(f"Found {len(files)} video files in subfolder")
                
                for file in files[:5]:  # Log first 5 files
                    logging.debug(f"  - {file['name']} (Created: {file.get('createdTime', 'N/A')})")
                
                return files
            else:
                logging.error(f"API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error listing videos: {e}")
            return None
    
    def get_latest_video(self, files):
        """Get the latest video from the list"""
        if not files or len(files) == 0:
            return None
        
        # Files are already sorted by createdTime desc from API
        latest = files[0]
        
        logging.info(f"Latest video: {latest['name']}")
        logging.info(f"  Created: {latest.get('createdTime', 'N/A')}")
        logging.info(f"  Size: {int(latest.get('size', 0)) / (1024*1024):.2f} MB")
        
        return latest
    
    def download_video(self, file_info):
        """Download video from Google Drive"""
        try:
            file_id = file_info['id']
            filename = file_info['name']
            
            # Create download folder
            download_path = self.config.get('download_folder', r"C:\TVVideos")
            Path(download_path).mkdir(parents=True, exist_ok=True)
            destination_path = os.path.join(download_path, filename)
            
            # Check if already downloaded and same file
            if os.path.exists(destination_path) and self.current_video_id == file_id:
                logging.info(f"Video already downloaded: {filename}")
                return destination_path
            
            # Download using Drive API
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={self.config['google_drive_api_key']}"
            
            logging.info(f"Downloading: {filename}")
            print(f"\n   📥 Downloading {filename}...")
            
            response = requests.get(url, stream=True, timeout=30)
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                
                # Download to temporary file first
                temp_path = destination_path + ".tmp"
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                speed = downloaded / (time.time() - start_time + 0.1) / 1024 / 1024
                                print(f"\r   Progress: {percent:.1f}% ({speed:.2f} MB/s)", end='')
                
                # Rename temp file to final name
                if os.path.exists(destination_path):
                    os.remove(destination_path)
                os.rename(temp_path, destination_path)
                
                print()
                logging.info(f"Download complete: {destination_path}")
                logging.info(f"Size: {downloaded / (1024*1024):.2f} MB")
                
                self.current_video_id = file_id
                self.current_video_name = filename
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
            self.config.get('vlc_path', r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
        
        for path in locations:
            if os.path.exists(path):
                logging.info(f"VLC found: {path}")
                return path
        
        logging.error("VLC not found")
        return None
    
    def play_video_smooth(self, video_path, is_update=False):
        """Play video with smooth transition"""
        with self.transition_lock:
            try:
                vlc_path = self.find_vlc()
                if not vlc_path:
                    return False
                
                if not os.path.exists(video_path):
                    logging.error(f"Video not found: {video_path}")
                    return False
                
                if is_update:
                    logging.info(f"Smooth transition to new video: {os.path.basename(video_path)}")
                    print(f"   🔄 Switching to new video...")
                else:
                    logging.info(f"Starting playback: {os.path.basename(video_path)}")
                    print(f"   🎬 Playing: {os.path.basename(video_path)}")
                
                # Get playback settings
                playback = self.config.get('playback_settings', {})
                
                # Build VLC command with smooth transition options
                cmd = [vlc_path]
                
                if playback.get('fullscreen', True):
                    cmd.append('--fullscreen')
                
                if playback.get('infinite_loop', True):
                    cmd.append('--loop')
                
                if not playback.get('show_video_title', False):
                    cmd.append('--no-video-title-show')
                
                if not playback.get('show_osd', False):
                    cmd.append('--no-osd')
                
                # Smooth transition settings
                cmd.extend([
                    '--video-on-top',  # Keep video on top
                    '--no-video-deco',  # No window decorations
                    '--no-embedded-video',  # Use separate window
                ])
                
                cmd.append(video_path)
                
                # If updating, stop old playback first
                if is_update and self.vlc_process:
                    logging.info("Stopping old playback for smooth transition...")
                    self.stop_playback()
                    time.sleep(0.5)  # Brief pause for smooth transition
                
                # Start new VLC process
                self.vlc_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                logging.info("VLC launched successfully")
                logging.info(f"VLC PID: {self.vlc_process.pid}")
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
                time.sleep(0.3)
                if self.vlc_process.poll() is None:
                    self.vlc_process.kill()
                    time.sleep(0.2)
                logging.info("Playback stopped")
        except Exception as e:
            logging.error(f"Error stopping playback: {e}")
    
    def is_vlc_running(self):
        """Check if VLC is still running"""
        if self.vlc_process:
            return self.vlc_process.poll() is None
        return False
    
    def monitor_subfolder(self):
        """Monitor subfolder for new videos and update if found"""
        monitoring = self.config.get('monitoring_settings', {})
        check_interval = monitoring.get('check_interval_seconds', 300)
        auto_restart = monitoring.get('auto_restart_on_crash', True)
        
        logging.info(f"Starting subfolder monitoring (every {check_interval} seconds)")
        print(f"\n   🔄 Monitoring subfolder for updates every {check_interval//60} minutes...")
        
        while self.monitoring:
            try:
                time.sleep(check_interval)
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"Checking subfolder for updates... ({current_time})")
                print(f"\n   🔍 Checking for new videos... ({datetime.now().strftime('%H:%M:%S')})")
                
                # List videos in subfolder
                files = self.list_videos_in_subfolder(self.subfolder_id)
                if not files:
                    logging.warning("Could not retrieve file list from subfolder")
                    continue
                
                # Get latest video
                latest_video = self.get_latest_video(files)
                if not latest_video:
                    logging.warning("No videos found in subfolder")
                    continue
                
                # Check if it's a new video
                if latest_video['id'] != self.current_video_id:
                    logging.info(f"New video detected in subfolder!")
                    logging.info(f"  Current: {self.current_video_name}")
                    logging.info(f"  New: {latest_video['name']}")
                    print(f"   🆕 New video detected!")
                    print(f"      Current: {self.current_video_name}")
                    print(f"      New: {latest_video['name']}")
                    
                    # Download new video
                    video_path = self.download_video(latest_video)
                    if video_path:
                        # Play with smooth transition
                        self.play_video_smooth(video_path, is_update=True)
                        print(f"   ✅ Smooth transition complete - now playing new video")
                else:
                    logging.info("No new videos - current is latest")
                    print(f"   ✓ No updates - current video is latest")
                
                # Auto-restart on crash if enabled
                if auto_restart and not self.is_vlc_running() and self.current_video_path:
                    logging.warning("VLC not running, restarting playback...")
                    print(f"   ⚠️  VLC stopped - restarting playback...")
                    self.play_video_smooth(self.current_video_path, is_update=False)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}", exc_info=True)
                print(f"   ⚠️  Monitoring error (will retry): {e}")
                time.sleep(60)
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        print("\n[1/6] Getting server's external IP address...")
        if not self.get_external_ip():
            print("   ❌ Failed to get external IP address")
            print("   This is required to find your subfolder")
            input("\nPress Enter to exit...")
            return
        print(f"   ✓ External IP: {self.external_ip}")
        
        print("\n[2/6] Finding subfolder for this TV...")
        subfolders = self.list_subfolders()
        if subfolders is None:
            print("   ❌ Failed to access Google Drive")
            print("   Please check your API key and main folder ID")
            input("\nPress Enter to exit...")
            return
        
        print(f"   Found {len(subfolders)} subfolders")
        
        my_subfolder = self.find_my_subfolder(subfolders)
        if not my_subfolder:
            print(f"   ❌ No subfolder found for IP: {self.external_ip}")
            print(f"\n   Available subfolders:")
            for folder in subfolders:
                print(f"      - {folder['name']}")
            print(f"\n   Please create a subfolder named: {self.external_ip}")
            input("\nPress Enter to exit...")
            return
        
        self.subfolder_id = my_subfolder['id']
        print(f"   ✓ Found subfolder: {my_subfolder['name']}")
        logging.info(f"Using subfolder: {my_subfolder['name']} (ID: {self.subfolder_id})")
        
        print("\n[3/6] Setting up local folders...")
        try:
            download_path = self.config.get('download_folder', r"C:\TVVideos")
            Path(download_path).mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Download folder: {download_path}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            input("\nPress Enter to exit...")
            return
        
        print("\n[4/6] Checking VLC installation...")
        if not self.find_vlc():
            print("   ❌ VLC not found")
            print("   Please install VLC Media Player")
            input("\nPress Enter to exit...")
            return
        print("   ✓ VLC found")
        
        print("\n[5/6] Getting latest video from subfolder...")
        files = self.list_videos_in_subfolder(self.subfolder_id)
        if not files:
            print(f"   ❌ No videos found in subfolder")
            print(f"\n   Please upload a video to subfolder: {my_subfolder['name']}")
            input("\nPress Enter to exit...")
            return
        
        latest_video = self.get_latest_video(files)
        print(f"   ✓ Found video: {latest_video['name']}")
        
        print("\n[6/6] Downloading and starting playback...")
        video_path = self.download_video(latest_video)
        if not video_path:
            print("   ❌ Download failed")
            input("\nPress Enter to exit...")
            return
        
        if not self.play_video_smooth(video_path, is_update=False):
            print("   ❌ Failed to start playback")
            input("\nPress Enter to exit...")
            return
        
        print("   ✅ Playback started in infinite loop!")
        
        monitoring = self.config.get('monitoring_settings', {})
        check_minutes = monitoring.get('check_interval_seconds', 300) // 60
        
        print("\n" + "="*70)
        print(f"✅ STATUS: Video playing in infinite loop")
        print(f"📁 Monitoring subfolder: {my_subfolder['name']}")
        print(f"🔄 Checking for updates every {check_minutes} minutes")
        print(f"🎬 Smooth transitions enabled for video updates")
        print(f"⚠️  Press Ctrl+C to stop")
        print("="*70)
        
        # Start monitoring in background
        if monitoring.get('enabled', True):
            monitor_thread = threading.Thread(target=self.monitor_subfolder, daemon=True)
            monitor_thread.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping application...")
            self.monitoring = False
            self.stop_playback()
            logging.info("Application stopped by user")
            print("✅ Goodbye!")

def main():
    """Entry point"""
    player = TVVideoPlayer()
    player.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n\n❌ Unexpected error: {e}")
        print(f"Check the log file for details")
        input("\nPress Enter to exit...")

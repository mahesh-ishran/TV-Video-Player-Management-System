"""
TV Video Player with Firebase Cloud Monitoring
Each TV sends status updates to Firebase Realtime Database
Dashboard reads from Firebase for live monitoring

Requirements:
    pip install requests firebase-admin psutil

Setup:
    1. Create Firebase project (free)
    2. Download service account JSON
    3. Update config file with database URL
"""

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
import psutil

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    print("❌ Firebase Admin SDK not installed!")
    print("Install with: pip install firebase-admin")
    sys.exit(1)


def load_config():
    """Load configuration from JSON file"""
    config_file = "tv_config_firebase.json"
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required = ['google_drive_api_key', 'main_folder_id', 'firebase_credentials_path', 'firebase_database_url']
        for field in required:
            if not config.get(field) or "YOUR_" in str(config[field]).upper():
                print(f"❌ Configuration error: {field} not set")
                sys.exit(1)
        
        return config
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)


CONFIG = load_config()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG.get('log_file', 'tv_video_player.log')),
        logging.StreamHandler(sys.stdout)
    ]
)


class FirebaseStatusReporter:
    """Handles sending status updates to Firebase"""
    
    def __init__(self, credentials_path, database_url, tv_id):
        self.tv_id = tv_id
        self.db_ref = None
        self.initialized = False
        
        try:
            # Initialize Firebase
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            
            # Get reference to this TV's data
            self.db_ref = db.reference(f'/tvs/{self.tv_id}')
            self.initialized = True
            logging.info("✅ Firebase connected successfully")
            
        except Exception as e:
            logging.error(f"❌ Firebase initialization error: {e}")
            self.initialized = False
    
    def send_status(self, status_data):
        """Send status update to Firebase"""
        if not self.initialized:
            logging.warning("Firebase not initialized, skipping status update")
            return False
        
        try:
            # Add timestamp
            status_data['last_update'] = datetime.now().isoformat()
            status_data['timestamp'] = int(time.time())
            
            # Update Firebase (this will merge with existing data)
            self.db_ref.update(status_data)
            
            logging.debug(f"📡 Status sent to Firebase: {status_data.get('status')}")
            return True
            
        except Exception as e:
            logging.error(f"Error sending status to Firebase: {e}")
            return False
    
    def report_playing(self, video_name, video_path):
        """Report that video is playing"""
        status_data = {
            'status': 'playing',
            'video_name': video_name,
            'video_path': video_path,
            'video_size_mb': round(os.path.getsize(video_path) / (1024 * 1024), 2) if os.path.exists(video_path) else 0,
            'connection_status': 'online'
        }
        self.send_status(status_data)
    
    def report_downloading(self, video_name):
        """Report that video is downloading"""
        status_data = {
            'status': 'downloading',
            'video_name': video_name,
            'connection_status': 'online'
        }
        self.send_status(status_data)
    
    def report_error(self, error_message):
        """Report error status"""
        status_data = {
            'status': 'error',
            'error_message': error_message,
            'connection_status': 'online'
        }
        self.send_status(status_data)
    
    def report_idle(self):
        """Report idle status (no video)"""
        status_data = {
            'status': 'idle',
            'message': 'No video to play',
            'connection_status': 'online'
        }
        self.send_status(status_data)
    
    def start_heartbeat(self, player_instance):
        """Start background thread for periodic heartbeat"""
        def heartbeat_loop():
            heartbeat_interval = CONFIG.get('monitoring_settings', {}).get('heartbeat_interval', 30)
            
            while player_instance.monitoring:
                try:
                    # Send current status
                    if hasattr(player_instance, 'current_video_path') and player_instance.current_video_path:
                        self.report_playing(
                            player_instance.current_video_name,
                            player_instance.current_video_path
                        )
                    else:
                        self.report_idle()
                    
                    time.sleep(heartbeat_interval)
                except Exception as e:
                    logging.error(f"Heartbeat error: {e}")
                    time.sleep(heartbeat_interval)
        
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        logging.info(f"💓 Heartbeat started (every {CONFIG.get('monitoring_settings', {}).get('heartbeat_interval', 30)}s)")


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
        self.status_reporter = None
        
    def print_header(self):
        """Print application header"""
        header = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     TV VIDEO PLAYER with FIREBASE MONITORING                     ║
║           Real-time cloud status reporting                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
        print(header)
        logging.info("="*70)
        logging.info("TV Video Player with Firebase Monitoring Started")
        logging.info("="*70)
    
    def kill_all_vlc_processes(self):
        """Kill all existing VLC processes"""
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'vlc' in proc.info['name'].lower():
                        logging.info(f"Killing existing VLC process: PID {proc.info['pid']}")
                        proc.kill()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if killed_count > 0:
                logging.info(f"Killed {killed_count} existing VLC process(es)")
                time.sleep(1)
                
        except Exception as e:
            logging.warning(f"Error killing VLC processes: {e}")
    
    def get_external_ip(self):
        """Get the server's external IP address"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logging.info(f"Hostname: {hostname}")
            logging.info(f"Local IP: {local_ip}")
            print(f"   Local IP: {local_ip}")
            
            logging.info("Fetching external IP address...")
            response = requests.get('https://api.ipify.org?format=text', timeout=10)
            external_ip = response.text.strip()
            
            # Replace dots with underscores for Firebase key (Firebase doesn't allow dots in keys)
            firebase_key = external_ip.replace('.', '_')
            
            logging.info(f"External IP: {external_ip}")
            logging.info(f"Firebase Key: {firebase_key}")
            print(f"   External IP: {external_ip}")
            print(f"   Firebase Key: {firebase_key}")
            
            self.external_ip = external_ip
            
            # Initialize Firebase status reporter
            self.status_reporter = FirebaseStatusReporter(
                self.config['firebase_credentials_path'],
                self.config['firebase_database_url'],
                firebase_key
            )
            
            return external_ip
            
        except Exception as e:
            logging.error(f"Error getting external IP: {e}")
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
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                folders = response.json().get('files', [])
                logging.info(f"Found {len(folders)} subfolders")
                return folders
            else:
                logging.error(f"API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error listing subfolders: {e}")
            return None
    
    def find_my_subfolder(self, subfolders):
        """Find subfolder matching this TV's external IP"""
        if not subfolders:
            return None
        
        for folder in subfolders:
            folder_name = folder['name'].strip()
            
            if folder_name == self.external_ip or self.external_ip in folder_name or folder_name in self.external_ip:
                logging.info(f"Found matching subfolder: {folder_name}")
                return folder
        
        logging.warning(f"No subfolder found matching IP: {self.external_ip}")
        return None
    
    def list_videos_in_subfolder(self, subfolder_id):
        """List all video files in the TV's subfolder"""
        try:
            url = "https://www.googleapis.com/drive/v3/files"
            params = {
                'q': f"'{subfolder_id}' in parents and trashed=false and (mimeType contains 'video/' or name contains '.mp4' or name contains '.avi' or name contains '.mkv')",
                'fields': 'files(id, name, createdTime, modifiedTime, size)',
                'key': self.config['google_drive_api_key'],
                'orderBy': 'createdTime desc'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                files = response.json().get('files', [])
                logging.info(f"Found {len(files)} video files")
                return files
            else:
                return None
                
        except Exception as e:
            logging.error(f"Error listing videos: {e}")
            return None
    
    def get_latest_video(self, files):
        """Get the latest video from the list"""
        if not files or len(files) == 0:
            return None
        
        latest = files[0]
        logging.info(f"Latest video: {latest['name']}")
        return latest
    
    def download_video(self, file_info):
        """Download video from Google Drive"""
        try:
            file_id = file_info['id']
            filename = file_info['name']
            
            # Report downloading status
            if self.status_reporter:
                self.status_reporter.report_downloading(filename)
            
            download_path = self.config.get('download_folder', r"C:\TVVideos")
            Path(download_path).mkdir(parents=True, exist_ok=True)
            destination_path = os.path.join(download_path, filename)
            
            if os.path.exists(destination_path) and self.current_video_id == file_id:
                logging.info(f"Video already downloaded: {filename}")
                return destination_path
            
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={self.config['google_drive_api_key']}"
            
            logging.info(f"Downloading: {filename}")
            print(f"\n   📥 Downloading {filename}...")
            
            response = requests.get(url, stream=True, timeout=30)
            
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                
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
                
                if os.path.exists(destination_path):
                    os.remove(destination_path)
                os.rename(temp_path, destination_path)
                
                print()
                logging.info(f"Download complete: {destination_path}")
                
                self.current_video_id = file_id
                self.current_video_name = filename
                return destination_path
            else:
                logging.error(f"Download failed: HTTP {response.status_code}")
                if self.status_reporter:
                    self.status_reporter.report_error(f"Download failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Download error: {e}")
            if self.status_reporter:
                self.status_reporter.report_error(f"Download error: {e}")
            return None
    
    def find_vlc(self):
        """Find VLC executable"""
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            self.config.get('vlc_path', '')
        ]
        
        for path in common_paths:
            if path and os.path.exists(path):
                logging.info(f"Found VLC: {path}")
                return path
        
        logging.error("VLC not found")
        return None
    
    def create_vlc_playlist(self, video_path):
        """Create a VLC playlist file"""
        try:
            download_path = self.config.get('download_folder', r"C:\TVVideos")
            playlist_path = os.path.join(download_path, "playlist.m3u8")
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write(f"#EXTINF:-1,{os.path.basename(video_path)}\n")
                f.write(f"{video_path}\n")
            
            logging.info(f"Created playlist: {playlist_path}")
            return playlist_path
            
        except Exception as e:
            logging.error(f"Error creating playlist: {e}")
            return None
    
    def play_video_loop(self, video_path, is_update=False):
        """Play video in infinite loop"""
        with self.transition_lock:
            try:
                vlc_path = self.find_vlc()
                if not vlc_path:
                    if self.status_reporter:
                        self.status_reporter.report_error("VLC not found")
                    return False
                
                if not os.path.exists(video_path):
                    logging.error(f"Video not found: {video_path}")
                    if self.status_reporter:
                        self.status_reporter.report_error(f"Video not found: {video_path}")
                    return False
                
                if is_update:
                    logging.info(f"Switching to new video: {os.path.basename(video_path)}")
                    print(f"   🔄 Switching to new video...")
                else:
                    logging.info(f"Starting playback: {os.path.basename(video_path)}")
                    print(f"   🎬 Playing: {os.path.basename(video_path)}")
                
                # Kill all VLC processes first
                self.kill_all_vlc_processes()
                time.sleep(1)
                
                # Get settings
                playback = self.config.get('playback_settings', {})
                
                # Create playlist
                playlist_path = self.create_vlc_playlist(video_path)
                
                # Build command
                cmd = [vlc_path]
                
                if playback.get('infinite_loop', True):
                    cmd.extend(['--repeat', '--loop'])
                
                if playback.get('fullscreen', True):
                    cmd.extend(['--fullscreen'])
                
                cmd.extend([
                    '--no-video-title-show',
                    '--no-osd',
                    '--video-on-top',
                    '--no-qt-fs-controller',
                    '--qt-start-minimized',
                    '--no-qt-system-tray',
                    '--qt-notification=0',
                    '--no-qt-error-dialogs',
                ])
                
                if playlist_path:
                    cmd.append(playlist_path)
                else:
                    cmd.append(video_path)
                
                # Start VLC
                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                self.vlc_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags
                )
                
                logging.info(f"VLC started - PID: {self.vlc_process.pid}")
                self.current_video_path = video_path
                
                # Report playing status to Firebase
                if self.status_reporter:
                    self.status_reporter.report_playing(
                        os.path.basename(video_path),
                        video_path
                    )
                
                return True
                
            except Exception as e:
                logging.error(f"Error playing video: {e}")
                if self.status_reporter:
                    self.status_reporter.report_error(f"Playback error: {e}")
                return False
    
    def is_vlc_running(self):
        """Check if VLC is still running"""
        if self.vlc_process:
            return self.vlc_process.poll() is None
        return False
    
    def monitor_subfolder(self):
        """Monitor subfolder for new videos"""
        monitoring = self.config.get('monitoring_settings', {})
        check_interval = monitoring.get('check_interval_seconds', 300)
        auto_restart = monitoring.get('auto_restart_on_crash', True)
        
        logging.info(f"Monitoring started (every {check_interval} seconds)")
        print(f"\n   🔄 Monitoring every {check_interval//60} minutes...")
        
        while self.monitoring:
            try:
                time.sleep(check_interval)
                
                logging.info("Checking for updates...")
                print(f"\n   🔍 Checking... ({datetime.now().strftime('%H:%M:%S')})")
                
                files = self.list_videos_in_subfolder(self.subfolder_id)
                if not files:
                    continue
                
                latest_video = self.get_latest_video(files)
                if not latest_video:
                    continue
                
                if latest_video['id'] != self.current_video_id:
                    logging.info(f"New video: {latest_video['name']}")
                    print(f"   🆕 New video detected!")
                    
                    video_path = self.download_video(latest_video)
                    if video_path:
                        self.play_video_loop(video_path, is_update=True)
                        print(f"   ✅ Now playing new video")
                else:
                    print(f"   ✓ No updates")
                
                if auto_restart and not self.is_vlc_running() and self.current_video_path:
                    logging.warning("VLC crashed - restarting...")
                    print(f"   ⚠️ Restarting VLC...")
                    self.play_video_loop(self.current_video_path, is_update=False)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(60)
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        print("\n[1/7] Getting external IP...")
        if not self.get_external_ip():
            print("   ❌ Failed")
            input("\nPress Enter to exit...")
            return
        print(f"   ✓ IP: {self.external_ip}")
        
        if not self.status_reporter or not self.status_reporter.initialized:
            print("\n   ❌ Firebase connection failed")
            print("   Check credentials and database URL")
            input("\nPress Enter to exit...")
            return
        print("   ✓ Firebase connected")
        
        print("\n[2/7] Finding subfolder...")
        subfolders = self.list_subfolders()
        if not subfolders:
            print("   ❌ Failed to list subfolders")
            if self.status_reporter:
                self.status_reporter.report_error("Failed to list subfolders")
            input("\nPress Enter to exit...")
            return
        
        my_subfolder = self.find_my_subfolder(subfolders)
        if not my_subfolder:
            print(f"   ❌ No subfolder for IP: {self.external_ip}")
            if self.status_reporter:
                self.status_reporter.report_error(f"No subfolder found for IP: {self.external_ip}")
            input("\nPress Enter to exit...")
            return
        
        self.subfolder_id = my_subfolder['id']
        print(f"   ✓ Subfolder: {my_subfolder['name']}")
        
        print("\n[3/7] Setting up...")
        Path(self.config.get('download_folder', r"C:\TVVideos")).mkdir(parents=True, exist_ok=True)
        print("   ✓ Folders ready")
        
        print("\n[4/7] Checking VLC...")
        if not self.find_vlc():
            print("   ❌ VLC not found")
            if self.status_reporter:
                self.status_reporter.report_error("VLC not found")
            input("\nPress Enter to exit...")
            return
        print("   ✓ VLC found")
        
        print("\n[5/7] Getting video...")
        files = self.list_videos_in_subfolder(self.subfolder_id)
        if not files:
            print("   ❌ No videos in subfolder")
            if self.status_reporter:
                self.status_reporter.report_idle()
            input("\nPress Enter to exit...")
            return
        
        latest = self.get_latest_video(files)
        print(f"   ✓ Video: {latest['name']}")
        
        print("\n[6/7] Downloading and playing...")
        video_path = self.download_video(latest)
        if not video_path:
            print("   ❌ Download failed")
            input("\nPress Enter to exit...")
            return
        
        if not self.play_video_loop(video_path):
            print("   ❌ Playback failed")
            input("\nPress Enter to exit...")
            return
        
        print("   ✅ Playing in infinite loop!")
        
        print("\n[7/7] Starting heartbeat...")
        if self.status_reporter:
            self.status_reporter.start_heartbeat(self)
        print("   ✅ Heartbeat active!")
        
        print("\n" + "="*70)
        print("✅ Video playing with Firebase monitoring enabled")
        print(f"☁️  Sending status to: Firebase Cloud")
        print(f"💓 Heartbeat every {self.config.get('monitoring_settings', {}).get('heartbeat_interval', 30)}s")
        print(f"🔄 Checking for updates every {self.config.get('monitoring_settings', {}).get('check_interval_seconds', 300)//60} min")
        print("⚠️  Press Ctrl+C to stop")
        print("="*70)
        
        if self.config.get('monitoring_settings', {}).get('enabled', True):
            monitor_thread = threading.Thread(target=self.monitor_subfolder, daemon=True)
            monitor_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping...")
            self.monitoring = False
            self.kill_all_vlc_processes()
            print("✅ Stopped")


def main():
    player = TVVideoPlayer()
    player.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        input("\nPress Enter to exit...")

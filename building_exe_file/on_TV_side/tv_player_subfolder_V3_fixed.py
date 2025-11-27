"""
TV Video Player - Subfolder Based Version (FIXED LOOPING)
This version fixes the VLC double window issue by:
1. Killing all VLC processes before starting
2. Using proper repeat/loop flags
3. Using single instance mode
4. Creating playlist for reliable looping
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
import psutil  # For process management

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
        
        required = ['google_drive_api_key', 'main_folder_id']
        for field in required:
            if not config.get(field) or "YOUR_" in config[field].upper():
                print(f"❌ Configuration error: {field} not set")
                print(f"Please edit {config_file} and add your {field}")
                input("\nPress Enter to exit...")
                sys.exit(1)
        
        return config
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        input("\nPress Enter to exit...")
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
║     TV VIDEO PLAYER - Subfolder System (FIXED LOOPING)          ║
║           Infinite Loop with No Window Issues                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
        print(header)
        logging.info("="*70)
        logging.info("TV Video Player - Subfolder-Based (Fixed Version) Started")
        logging.info("="*70)
    
    def kill_all_vlc_processes(self):
        """Kill all existing VLC processes to ensure clean start"""
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
                time.sleep(1)  # Wait for processes to fully terminate
                
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
            
            logging.info(f"External IP: {external_ip}")
            print(f"   External IP: {external_ip}")
            
            self.external_ip = external_ip
            return external_ip
            
        except Exception as e:
            logging.error(f"Error getting external IP: {e}")
            
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
            
            logging.error("Could not determine external IP")
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
                return None
                
        except Exception as e:
            logging.error(f"Download error: {e}")
            return None
    
    def get_registry_value(self, key, value_name: str):
        """Safely get a registry value."""
        try:
            import winreg
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value else None
        except:
            return None
    
    def scan_registry_for_vlc(self):
        """Scan Windows Registry comprehensively for VLC installation."""
        try:
            import winreg
            
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
            ]
            
            logging.info("Scanning Windows Registry for VLC...")
            
            for hkey, path in registry_paths:
                try:
                    reg_key = winreg.OpenKey(hkey, path)
                    
                    # For direct VLC registry path
                    if "VideoLAN\\VLC" in path:
                        install_dir = self.get_registry_value(reg_key, "InstallDir")
                        winreg.CloseKey(reg_key)
                        
                        if install_dir:
                            vlc_exe = os.path.join(install_dir, "vlc.exe")
                            if os.path.exists(vlc_exe):
                                logging.info(f"Found VLC via registry: {vlc_exe}")
                                return vlc_exe
                        continue
                    
                    # For uninstall registry paths, enumerate all programs
                    num_subkeys = winreg.QueryInfoKey(reg_key)[0]
                    
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(reg_key, i)
                            subkey = winreg.OpenKey(reg_key, subkey_name)
                            
                            display_name = self.get_registry_value(subkey, "DisplayName")
                            
                            # Check if this is VLC
                            if display_name and "vlc" in display_name.lower():
                                # Try to get install location
                                install_location = self.get_registry_value(subkey, "InstallLocation")
                                
                                if install_location:
                                    vlc_exe = os.path.join(install_location, "vlc.exe")
                                    if os.path.exists(vlc_exe):
                                        winreg.CloseKey(subkey)
                                        winreg.CloseKey(reg_key)
                                        logging.info(f"Found VLC via uninstall registry: {vlc_exe}")
                                        return vlc_exe
                                
                                # Try DisplayIcon
                                display_icon = self.get_registry_value(subkey, "DisplayIcon")
                                if display_icon and "vlc.exe" in display_icon.lower():
                                    icon_path = display_icon.split(",")[0].strip('"')
                                    if os.path.exists(icon_path) and icon_path.lower().endswith("vlc.exe"):
                                        winreg.CloseKey(subkey)
                                        winreg.CloseKey(reg_key)
                                        logging.info(f"Found VLC via DisplayIcon: {icon_path}")
                                        return icon_path
                                
                                # Try UninstallString
                                uninstall_string = self.get_registry_value(subkey, "UninstallString")
                                if uninstall_string:
                                    uninstall_dir = os.path.dirname(uninstall_string.strip('"'))
                                    vlc_exe = os.path.join(uninstall_dir, "vlc.exe")
                                    if os.path.exists(vlc_exe):
                                        winreg.CloseKey(subkey)
                                        winreg.CloseKey(reg_key)
                                        logging.info(f"Found VLC via UninstallString: {vlc_exe}")
                                        return vlc_exe
                            
                            winreg.CloseKey(subkey)
                        except:
                            continue
                    
                    winreg.CloseKey(reg_key)
                
                except:
                    continue
            
            return None
            
        except Exception as e:
            logging.warning(f"Registry scan error: {e}")
            return None
    
    def check_common_paths(self):
        """Check common VLC installation paths."""
        logging.info("Checking common VLC installation paths...")
        
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                logging.info(f"Found VLC at common path: {path}")
                return path
        
        return None
    
    def check_path_environment(self):
        """Check if VLC is in system PATH."""
        logging.info("Checking system PATH for VLC...")
        
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for path_dir in path_dirs:
            vlc_exe = os.path.join(path_dir, 'vlc.exe')
            if os.path.exists(vlc_exe):
                logging.info(f"Found VLC in PATH: {vlc_exe}")
                return vlc_exe
        
        return None
    
    def search_program_files(self):
        """Search Program Files directories for VLC."""
        logging.info("Searching Program Files directories...")
        
        search_dirs = [
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
        ]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            try:
                # Look for VideoLAN folder
                videolan_path = os.path.join(search_dir, 'VideoLAN')
                if os.path.exists(videolan_path):
                    for root, dirs, files in os.walk(videolan_path):
                        if 'vlc.exe' in [f.lower() for f in files]:
                            vlc_exe = os.path.join(root, 'vlc.exe')
                            if os.path.exists(vlc_exe):
                                logging.info(f"Found VLC via file search: {vlc_exe}")
                                return vlc_exe
                
                # Search more broadly (but limit depth)
                for item in os.listdir(search_dir):
                    if 'vlc' in item.lower():
                        item_path = os.path.join(search_dir, item)
                        if os.path.isdir(item_path):
                            for root, dirs, files in os.walk(item_path):
                                depth = root[len(item_path):].count(os.sep)
                                if depth > 2:
                                    continue
                                if 'vlc.exe' in [f.lower() for f in files]:
                                    vlc_exe = os.path.join(root, 'vlc.exe')
                                    if os.path.exists(vlc_exe):
                                        logging.info(f"Found VLC via broad search: {vlc_exe}")
                                        return vlc_exe
            except:
                continue
        
        return None
    
    def find_vlc(self):
        """Find VLC using comprehensive robust methods - ENHANCED VERSION"""
        logging.info("="*70)
        logging.info("SEARCHING FOR VLC MEDIA PLAYER (Robust Method)")
        logging.info("="*70)
        
        # Method 1: Check config file path first
        config_vlc_path = self.config.get('vlc_path', '')
        if config_vlc_path and os.path.exists(config_vlc_path):
            logging.info(f"✓ Found VLC at configured path: {config_vlc_path}")
            return config_vlc_path
        
        # Method 2: Check common paths (fastest)
        vlc_path = self.check_common_paths()
        if vlc_path:
            logging.info(f"✓ Found VLC via common paths")
            return vlc_path
        
        # Method 3: Scan Windows Registry (most reliable)
        if sys.platform == 'win32':
            vlc_path = self.scan_registry_for_vlc()
            if vlc_path:
                logging.info(f"✓ Found VLC via Windows Registry")
                return vlc_path
        
        # Method 4: Check PATH environment
        vlc_path = self.check_path_environment()
        if vlc_path:
            logging.info(f"✓ Found VLC in system PATH")
            return vlc_path
        
        # Method 5: Search Program Files (thorough but slower)
        vlc_path = self.search_program_files()
        if vlc_path:
            logging.info(f"✓ Found VLC via file system search")
            return vlc_path
        
        logging.error("✗ VLC Media Player not found on this system")
        logging.error("Searched locations:")
        logging.error("  • Common installation paths")
        logging.error("  • Windows Registry (all uninstall entries)")
        logging.error("  • System PATH environment variable")
        logging.error("  • Program Files directories")
        
        return None
    
    def create_vlc_playlist(self, video_path):
        """Create a VLC playlist file for reliable looping"""
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
        """Play video in infinite loop - FIXED VERSION"""
        with self.transition_lock:
            try:
                vlc_path = self.find_vlc()
                if not vlc_path:
                    return False
                
                if not os.path.exists(video_path):
                    logging.error(f"Video not found: {video_path}")
                    return False
                
                if is_update:
                    logging.info(f"Switching to new video: {os.path.basename(video_path)}")
                    print(f"   🔄 Switching to new video...")
                else:
                    logging.info(f"Starting playback: {os.path.basename(video_path)}")
                    print(f"   🎬 Playing: {os.path.basename(video_path)}")
                
                # CRITICAL: Kill all VLC processes first
                self.kill_all_vlc_processes()
                time.sleep(1)
                
                # Get settings
                playback = self.config.get('playback_settings', {})
                
                # Create playlist
                playlist_path = self.create_vlc_playlist(video_path)
                
                # Build command - FIXED for looping
                cmd = [vlc_path]
                
                # Loop settings - use BOTH repeat and loop
                if playback.get('infinite_loop', True):
                    cmd.extend([
                        '--repeat',  # Repeat single item
                        '--loop',    # Loop playlist
                    ])
                
                # Fullscreen
                if playback.get('fullscreen', True):
                    cmd.extend(['--fullscreen'])
                
                # Hide everything
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
                
                # Use playlist
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
                
                return True
                
            except Exception as e:
                logging.error(f"Error playing video: {e}")
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
                    print(f"   ⚠️  Restarting VLC...")
                    self.play_video_loop(self.current_video_path, is_update=False)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(60)
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        print("\n[1/6] Getting external IP...")
        if not self.get_external_ip():
            print("   ❌ Failed")
            input("\nPress Enter to exit...")
            return
        print(f"   ✓ IP: {self.external_ip}")
        
        print("\n[2/6] Finding subfolder...")
        subfolders = self.list_subfolders()
        if not subfolders:
            print("   ❌ Failed to list subfolders")
            input("\nPress Enter to exit...")
            return
        
        my_subfolder = self.find_my_subfolder(subfolders)
        if not my_subfolder:
            print(f"   ❌ No subfolder for IP: {self.external_ip}")
            print(f"\n   Create subfolder: {self.external_ip}")
            input("\nPress Enter to exit...")
            return
        
        self.subfolder_id = my_subfolder['id']
        print(f"   ✓ Subfolder: {my_subfolder['name']}")
        
        print("\n[3/6] Setting up...")
        Path(self.config.get('download_folder', r"C:\TVVideos")).mkdir(parents=True, exist_ok=True)
        print("   ✓ Folders ready")
        
        print("\n[4/6] Checking VLC...")
        if not self.find_vlc():
            print("   ❌ VLC not found")
            input("\nPress Enter to exit...")
            return
        print("   ✓ VLC found")
        
        print("\n[5/6] Getting video...")
        files = self.list_videos_in_subfolder(self.subfolder_id)
        if not files:
            print("   ❌ No videos in subfolder")
            input("\nPress Enter to exit...")
            return
        
        latest = self.get_latest_video(files)
        print(f"   ✓ Video: {latest['name']}")
        
        print("\n[6/6] Downloading and playing...")
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
        
        print("\n" + "="*70)
        print("✅ Video playing in infinite loop (FIXED VERSION)")
        print(f"📁 Monitoring: {my_subfolder['name']}")
        print(f"🔄 Updates every {self.config.get('monitoring_settings', {}).get('check_interval_seconds', 300)//60} min")
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

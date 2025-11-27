"""
VLC Auto Video Player with HTTP Interface (Reliable Version)
This script uses VLC's HTTP interface or playlist approach to switch videos smoothly.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python vlc_auto_player_fixed.py
    python vlc_auto_player_fixed.py --folder "C:\Videos"
    python vlc_auto_player_fixed.py --folder "C:\Videos" --check-interval 60
"""

import os
import sys
import time
import winreg
import subprocess
import argparse
import urllib.request
import urllib.parse
import base64
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import xml.etree.ElementTree as ET


class VLCFinder:
    """Class to find VLC media player installation."""
    
    def __init__(self):
        self.vlc_path = None
    
    def find_vlc(self) -> Optional[str]:
        """Find VLC installation path."""
        print("Searching for VLC Media Player...")
        print("-" * 80)
        
        # Method 1: Check common installation paths
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', ''), 'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                print(f"✓ Found VLC at: {path}")
                self.vlc_path = path
                return path
        
        # Method 2: Check registry
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
        ]
        
        for hkey, reg_path in registry_paths:
            try:
                reg_key = winreg.OpenKey(hkey, reg_path)
                install_dir, _ = winreg.QueryValueEx(reg_key, "InstallDir")
                reg_key.Close()
                
                vlc_exe = os.path.join(install_dir, "vlc.exe")
                if os.path.exists(vlc_exe):
                    print(f"✓ Found VLC at: {vlc_exe}")
                    self.vlc_path = vlc_exe
                    return vlc_exe
            except:
                continue
        
        # Method 3: Check PATH environment variable
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for path_dir in path_dirs:
            vlc_exe = os.path.join(path_dir, 'vlc.exe')
            if os.path.exists(vlc_exe):
                print(f"✓ Found VLC at: {vlc_exe}")
                self.vlc_path = vlc_exe
                return vlc_exe
        
        print("✗ VLC Media Player not found!")
        print("\nPlease install VLC from: https://www.videolan.org/vlc/")
        return None


class VLCHTTPControl:
    """Class to control VLC via HTTP interface."""
    
    def __init__(self, host='localhost', port=8080, password='admin'):
        self.host = host
        self.port = port
        self.password = password
        self.base_url = f"http://{host}:{port}"
        
        # Create authorization header
        credentials = base64.b64encode(f":{password}".encode()).decode()
        self.auth_header = f"Basic {credentials}"
    
    def send_command(self, command: str, params: dict = None) -> bool:
        """Send command to VLC HTTP interface."""
        try:
            url = f"{self.base_url}/requests/status.xml?command={command}"
            
            if params:
                param_str = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
                url += f"&{param_str}"
            
            request = urllib.request.Request(url)
            request.add_header("Authorization", self.auth_header)
            
            response = urllib.request.urlopen(request, timeout=5)
            return response.status == 200
        
        except Exception as e:
            return False
    
    def test_connection(self) -> bool:
        """Test if HTTP interface is accessible."""
        try:
            request = urllib.request.Request(f"{self.base_url}/requests/status.xml")
            request.add_header("Authorization", self.auth_header)
            response = urllib.request.urlopen(request, timeout=5)
            return response.status == 200
        except:
            return False
    
    def clear_playlist(self) -> bool:
        """Clear the current playlist."""
        return self.send_command("pl_empty")
    
    def add_to_playlist(self, video_path: str) -> bool:
        """Add video to playlist."""
        file_uri = Path(video_path).as_uri()
        return self.send_command("in_enqueue", {"input": file_uri})
    
    def play(self) -> bool:
        """Start playback."""
        return self.send_command("pl_play")
    
    def set_loop(self, enable: bool = True) -> bool:
        """Enable/disable loop mode."""
        return self.send_command("pl_loop")
    
    def set_repeat(self, enable: bool = True) -> bool:
        """Enable/disable repeat mode."""
        return self.send_command("pl_repeat")


class VideoMonitor:
    """Class to monitor folder for videos and control VLC playback."""
    
    # Supported video file extensions
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob'
    }
    
    def __init__(self, vlc_path: str, folder_path: str, check_interval: int = 60):
        """
        Initialize VideoMonitor.
        
        Args:
            vlc_path: Path to VLC executable
            folder_path: Folder to monitor for videos
            check_interval: Seconds between checks for new videos
        """
        self.vlc_path = vlc_path
        self.folder_path = Path(folder_path)
        self.check_interval = check_interval
        self.current_video = None
        self.vlc_process = None
        self.vlc_http = None
        self.http_port = 8080
        self.http_password = "vlcremote"
        
        if not self.folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        
        if not self.folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
    
    def get_video_files(self) -> List[Path]:
        """Get all video files in the folder."""
        video_files = []
        
        try:
            for file in self.folder_path.iterdir():
                if file.is_file() and file.suffix.lower() in self.VIDEO_EXTENSIONS:
                    video_files.append(file)
        except Exception as e:
            print(f"Error scanning folder: {e}")
        
        return video_files
    
    def get_latest_video(self) -> Optional[Path]:
        """Get the most recently modified video file."""
        video_files = self.get_video_files()
        
        if not video_files:
            return None
        
        # Sort by modification time (newest first)
        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return video_files[0]
    
    def is_vlc_running(self) -> bool:
        """Check if VLC process is still running."""
        if self.vlc_process is None:
            return False
        
        return self.vlc_process.poll() is None
    
    def start_vlc_with_http(self, initial_video: Optional[Path] = None):
        """Start VLC with HTTP interface enabled."""
        try:
            print(f"\nStarting VLC with HTTP interface on port {self.http_port}...")
            
            # VLC command with HTTP interface
            command = [
                self.vlc_path,
                '--intf', 'http',  # Enable HTTP interface
                '--http-host', f'localhost',
                '--http-port', str(self.http_port),
                '--http-password', self.http_password,
                '--repeat',  # Enable repeat for single video looping
                '--no-video-title-show',  # Don't show filename on video
                '--extraintf', 'http',  # Run HTTP in addition to main interface
            ]
            
            # Add initial video if provided
            if initial_video:
                command.append(str(initial_video))
            
            # Start VLC process
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            print("✓ VLC started with HTTP interface")
            
            # Give VLC time to start
            print("Waiting for VLC to initialize...")
            time.sleep(3)
            
            # Connect to HTTP interface
            print("Connecting to VLC HTTP interface...")
            self.vlc_http = VLCHTTPControl(port=self.http_port, password=self.http_password)
            
            # Test connection with retries
            max_retries = 10
            for i in range(max_retries):
                if self.vlc_http.test_connection():
                    print("✓ Connected to VLC HTTP interface")
                    
                    # Enable repeat mode
                    self.vlc_http.set_repeat(True)
                    
                    return True
                
                if i < max_retries - 1:
                    print(f"  Retry {i+1}/{max_retries}...")
                    time.sleep(2)
            
            print("✗ Failed to connect to VLC HTTP interface")
            print("\nTrying alternative playlist-based approach...")
            return False
        
        except Exception as e:
            print(f"✗ Error starting VLC: {e}")
            return False
    
    def switch_video_http(self, video_path: Path) -> bool:
        """Switch to a new video using HTTP interface."""
        try:
            print(f"\n{'=' * 80}")
            print(f"🎬 Switching to: {video_path.name}")
            print(f"Location: {video_path}")
            print(f"Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"Modified: {datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}")
            
            # Clear playlist
            if not self.vlc_http.clear_playlist():
                print("Warning: Could not clear playlist")
            
            time.sleep(0.5)
            
            # Add new video
            if not self.vlc_http.add_to_playlist(str(video_path)):
                print("Warning: Could not add video to playlist")
            
            time.sleep(0.5)
            
            # Play
            if not self.vlc_http.play():
                print("Warning: Could not start playback")
            
            time.sleep(0.5)
            
            # Enable repeat
            self.vlc_http.set_repeat(True)
            
            self.current_video = video_path
            print("✓ Video switched successfully\n")
            return True
        
        except Exception as e:
            print(f"✗ Error switching video: {e}")
            return False
    
    def restart_vlc_with_video(self, video_path: Path):
        """Restart VLC with new video (fallback method)."""
        print(f"\n{'*' * 80}")
        print("🔄 Restarting VLC with new video...")
        print(f"{'*' * 80}")
        
        # Stop current VLC
        if self.vlc_process and self.is_vlc_running():
            try:
                self.vlc_process.terminate()
                self.vlc_process.wait(timeout=3)
            except:
                try:
                    self.vlc_process.kill()
                except:
                    pass
        
        # Wait a moment
        time.sleep(1)
        
        # Start VLC with the new video
        self.start_vlc_with_http(video_path)
        self.current_video = video_path
    
    def monitor_and_play(self):
        """Main monitoring loop."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Press Ctrl+C to stop monitoring")
        print("=" * 80)
        
        # Initial check for videos
        latest_video = self.get_latest_video()
        
        if not latest_video:
            print("\n⚠ No video files found in folder")
            print("Waiting for videos to be added...")
        else:
            print(f"\nFound {len(self.get_video_files())} video(s) in folder")
        
        # Start VLC with HTTP interface
        http_working = self.start_vlc_with_http(latest_video)
        
        if latest_video:
            self.current_video = latest_video
            print(f"\n✓ Playing: {latest_video.name}")
        
        # Monitoring loop
        try:
            last_status_time = time.time()
            http_failed_count = 0
            
            while True:
                time.sleep(self.check_interval)
                
                # Check if VLC is still running
                if not self.is_vlc_running():
                    print("\n⚠ VLC was closed by user. Exiting monitor...")
                    break
                
                # Check for latest video
                latest_video = self.get_latest_video()
                
                if latest_video is None:
                    # No videos in folder
                    if self.current_video is not None:
                        print("\n⚠ All videos removed from folder")
                        if http_working and self.vlc_http:
                            self.vlc_http.clear_playlist()
                        self.current_video = None
                    continue
                
                # Check if there's a new video
                if self.current_video is None or latest_video != self.current_video:
                    print(f"\n{'*' * 80}")
                    print("📹 NEW VIDEO DETECTED!")
                    print(f"{'*' * 80}")
                    
                    if http_working and self.vlc_http:
                        # Try HTTP control
                        success = self.switch_video_http(latest_video)
                        
                        if not success:
                            http_failed_count += 1
                            
                            # If HTTP fails multiple times, fall back to restart method
                            if http_failed_count >= 3:
                                print("⚠ HTTP control not working reliably, switching to restart method")
                                http_working = False
                                self.restart_vlc_with_video(latest_video)
                        else:
                            http_failed_count = 0
                    else:
                        # Use restart method
                        self.restart_vlc_with_video(latest_video)
                    
                    last_status_time = time.time()
                
                # Show status every 60 seconds
                if time.time() - last_status_time >= 60:
                    video_count = len(self.get_video_files())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Playing: {self.current_video.name if self.current_video else 'None'} | "
                          f"Videos in folder: {video_count}")
                    last_status_time = time.time()
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("MONITORING STOPPED BY USER")
            print("=" * 80)
        
        except Exception as e:
            print(f"\n✗ Error in monitoring loop: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print("\n✓ Monitoring stopped. VLC is still running.")
            print("You can close VLC manually when done.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Auto-play latest video with VLC (HTTP interface + fallback)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vlc_auto_player_fixed.py
  python vlc_auto_player_fixed.py --folder "C:\\TVVideos"
  python vlc_auto_player_fixed.py --folder "C:\\TVVideos" --check-interval 60

Features:
  - Uses VLC's HTTP interface for smooth control
  - Falls back to restart method if HTTP fails
  - Plays latest video in infinite loop
  - Monitors folder for new videos
  - Minimizes interruptions during video switching
        """
    )
    
    parser.add_argument('--folder', type=str,
                       help='Folder path to monitor for videos (default: current directory)')
    parser.add_argument('--check-interval', type=int, default=60,
                       help='Seconds between folder checks (default: 60)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER (HTTP + Fallback Mode)")
    print("=" * 80)
    print()
    
    # Find VLC
    vlc_finder = VLCFinder()
    vlc_path = vlc_finder.find_vlc()
    
    if not vlc_path:
        print("\n❌ Cannot proceed without VLC Media Player")
        print("\nPlease:")
        print("1. Install VLC from https://www.videolan.org/vlc/")
        print("2. Run this script again")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print()
    
    # Determine folder to monitor
    if args.folder:
        folder_path = args.folder
    else:
        folder_path = os.getcwd()
        print(f"No folder specified, using current directory: {folder_path}")
    
    # Create monitor and start
    try:
        monitor = VideoMonitor(vlc_path, folder_path, args.check_interval)
        monitor.monitor_and_play()
    
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("\nScript finished. VLC is still running.")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

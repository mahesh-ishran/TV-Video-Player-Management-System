"""
VLC Auto Video Player with Remote Control (No Minimize Issue)
This script uses VLC's Remote Control interface to switch videos smoothly
without closing and reopening VLC, preventing the minimization issue.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python vlc_auto_player_rc.py
    python vlc_auto_player_rc.py --folder "C:\Videos"
    python vlc_auto_player_rc.py --folder "C:\Videos" --check-interval 5
"""

import os
import sys
import time
import winreg
import subprocess
import socket
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime


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


class VLCRemoteControl:
    """Class to control VLC via RC interface."""
    
    def __init__(self, host='localhost', port=9999, password='admin'):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
    
    def connect(self, max_retries=10, retry_delay=1) -> bool:
        """Connect to VLC RC interface."""
        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)
                self.socket.connect((self.host, self.port))
                
                # Read welcome message
                welcome = self.socket.recv(1024).decode('utf-8', errors='ignore')
                
                # Send password if required
                if 'Password' in welcome:
                    self.send_command(self.password, wait_response=True)
                
                return True
            
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return False
        
        return False
    
    def send_command(self, command: str, wait_response=True) -> Optional[str]:
        """Send command to VLC and optionally wait for response."""
        if not self.socket:
            return None
        
        try:
            # Send command
            self.socket.sendall(f"{command}\n".encode('utf-8'))
            
            if wait_response:
                # Wait a bit for response
                time.sleep(0.1)
                response = self.socket.recv(4096).decode('utf-8', errors='ignore')
                return response
            
            return None
        
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def clear_playlist(self):
        """Clear the current playlist."""
        self.send_command("clear", wait_response=False)
    
    def add_to_playlist(self, video_path: str):
        """Add video to playlist."""
        # Escape path for VLC
        escaped_path = str(video_path).replace('\\', '/')
        self.send_command(f'add "{escaped_path}"', wait_response=False)
    
    def play(self):
        """Start playback."""
        self.send_command("play", wait_response=False)
    
    def stop(self):
        """Stop playback."""
        self.send_command("stop", wait_response=False)
    
    def loop_on(self):
        """Enable loop mode."""
        self.send_command("loop on", wait_response=False)
    
    def repeat_on(self):
        """Enable repeat mode."""
        self.send_command("repeat on", wait_response=False)
    
    def close(self):
        """Close connection."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None


class VideoMonitor:
    """Class to monitor folder for videos and control VLC playback."""
    
    # Supported video file extensions
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob'
    }
    
    def __init__(self, vlc_path: str, folder_path: str, check_interval: int = 3):
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
        self.vlc_rc = None
        self.rc_port = 9999
        
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
    
    def start_vlc_with_rc(self):
        """Start VLC with Remote Control interface enabled."""
        try:
            print(f"\nStarting VLC with Remote Control interface on port {self.rc_port}...")
            
            # VLC command with RC interface
            command = [
                self.vlc_path,
                '--intf', 'rc',  # Enable RC interface
                '--rc-host', f'localhost:{self.rc_port}',  # RC interface host and port
                '--rc-quiet',  # Quiet mode for RC
                '--loop',  # Enable playlist looping
                '--no-video-title-show',  # Don't show filename on video
            ]
            
            # Start VLC process
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            print("✓ VLC started with RC interface")
            
            # Give VLC a moment to start
            time.sleep(2)
            
            # Connect to RC interface
            print("Connecting to VLC Remote Control...")
            self.vlc_rc = VLCRemoteControl(port=self.rc_port)
            
            if self.vlc_rc.connect():
                print("✓ Connected to VLC Remote Control interface")
                
                # Enable repeat mode for single video looping
                self.vlc_rc.repeat_on()
                
                return True
            else:
                print("✗ Failed to connect to VLC Remote Control")
                return False
        
        except Exception as e:
            print(f"✗ Error starting VLC: {e}")
            return False
    
    def switch_video(self, video_path: Path):
        """
        Switch to a new video using RC interface (no restart, no minimize).
        
        Args:
            video_path: Path to the video file
        """
        try:
            print(f"\n{'=' * 80}")
            print(f"🎬 Switching to: {video_path.name}")
            print(f"Location: {video_path}")
            print(f"Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"Modified: {datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}")
            
            # Clear current playlist
            self.vlc_rc.clear_playlist()
            time.sleep(0.3)
            
            # Add new video to playlist
            self.vlc_rc.add_to_playlist(str(video_path))
            time.sleep(0.3)
            
            # Start playback
            self.vlc_rc.play()
            time.sleep(0.3)
            
            # Ensure repeat is on for looping
            self.vlc_rc.repeat_on()
            
            self.current_video = video_path
            print("✓ Video switched successfully (VLC window stays open)\n")
        
        except Exception as e:
            print(f"✗ Error switching video: {e}")
    
    def monitor_and_play(self):
        """Main monitoring loop - continuously check for new videos and play them."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Press Ctrl+C to stop monitoring")
        print("=" * 80)
        
        # Start VLC with RC interface
        if not self.start_vlc_with_rc():
            print("\n❌ Failed to start VLC with Remote Control interface")
            return
        
        # Initial check for videos
        latest_video = self.get_latest_video()
        
        if latest_video:
            print(f"\nFound {len(self.get_video_files())} video(s) in folder")
            self.switch_video(latest_video)
        else:
            print("\n⚠ No video files found in folder")
            print("Waiting for videos to be added...")
        
        # Monitoring loop
        try:
            last_status_time = time.time()
            
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
                        self.vlc_rc.clear_playlist()
                        self.current_video = None
                    continue
                
                # Check if there's a new video (different from current)
                if self.current_video is None or latest_video != self.current_video:
                    print(f"\n{'*' * 80}")
                    print("📹 NEW VIDEO DETECTED!")
                    print(f"{'*' * 80}")
                    self.switch_video(latest_video)
                    last_status_time = time.time()  # Reset status timer after video change
                
                # Show status every 30 seconds
                if time.time() - last_status_time >= 30:
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
            # Cleanup
            if self.vlc_rc:
                self.vlc_rc.close()
            
            # Don't kill VLC - let user close it manually if they want
            print("\n✓ Monitoring stopped. VLC is still running.")
            print("You can close VLC manually when done.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Auto-play latest video with VLC using Remote Control (no minimize issue)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vlc_auto_player_rc.py
  python vlc_auto_player_rc.py --folder "C:\\Users\\YourName\\Videos"
  python vlc_auto_player_rc.py --folder "D:\\Movies" --check-interval 5

Features:
  - Uses VLC's Remote Control interface (no restart, no minimize)
  - Plays latest video in infinite loop
  - Monitors folder for new videos
  - Smoothly switches to new video without closing VLC
  - VLC window stays open and focused
        """
    )
    
    parser.add_argument('--folder', type=str,
                       help='Folder path to monitor for videos (default: current directory)')
    parser.add_argument('--check-interval', type=int, default=3,
                       help='Seconds between folder checks (default: 3)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER (Remote Control Mode)")
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

"""
VLC Auto Video Player with Folder Monitoring
This script finds VLC media player, plays the latest video in a folder in infinite loop,
and automatically switches to new videos when they are added to the folder.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python vlc_auto_player.py
    python vlc_auto_player.py --folder "C:\Videos"
    python vlc_auto_player.py --folder "C:\Videos" --check-interval 5
"""

import os
import sys
import time
import winreg
import subprocess
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


class VideoMonitor:
    """Class to monitor folder for videos and play them with VLC."""
    
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
        
        # Check if process is still alive
        return self.vlc_process.poll() is None
    
    def stop_vlc(self):
        """Stop the current VLC process."""
        if self.vlc_process and self.is_vlc_running():
            try:
                self.vlc_process.terminate()
                # Wait up to 2 seconds for graceful termination
                self.vlc_process.wait(timeout=2)
                print("✓ Stopped current video playback")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                self.vlc_process.kill()
                print("✓ Force stopped current video playback")
            except Exception as e:
                print(f"Warning: Error stopping VLC: {e}")
            
            self.vlc_process = None
    
    def play_video(self, video_path: Path):
        """
        Play a video file with VLC in loop mode.
        
        Args:
            video_path: Path to the video file
        """
        try:
            # Stop current video if playing
            self.stop_vlc()
            
            print(f"\n{'=' * 80}")
            print(f"Playing: {video_path.name}")
            print(f"Location: {video_path}")
            print(f"Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"Modified: {datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}\n")
            
            # VLC command with loop option
            # --loop or --repeat will loop the current video infinitely
            command = [
                self.vlc_path,
                str(video_path),
                '--loop',  # Loop the playlist
                '--no-video-title-show',  # Don't show filename on video
            ]
            
            # Start VLC process
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.current_video = video_path
            
        except Exception as e:
            print(f"✗ Error playing video: {e}")
            self.vlc_process = None
    
    def monitor_and_play(self):
        """Main monitoring loop - continuously check for new videos and play them."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Press Ctrl+C to stop monitoring")
        print("=" * 80)
        
        # Initial check for videos
        latest_video = self.get_latest_video()
        
        if latest_video:
            print(f"\nFound {len(self.get_video_files())} video(s) in folder")
            self.play_video(latest_video)
        else:
            print("\n⚠ No video files found in folder")
            print("Waiting for videos to be added...")
        
        # Monitoring loop
        try:
            while True:
                time.sleep(self.check_interval)
                
                # Check for latest video
                latest_video = self.get_latest_video()
                
                if latest_video is None:
                    # No videos in folder
                    if self.current_video is not None:
                        print("\n⚠ All videos removed from folder")
                        self.stop_vlc()
                        self.current_video = None
                    continue
                
                # Check if there's a new video (different from current)
                if self.current_video is None or latest_video != self.current_video:
                    print(f"\n{'*' * 80}")
                    print("🎬 NEW VIDEO DETECTED!")
                    print(f"{'*' * 80}")
                    self.play_video(latest_video)
                
                # Check if VLC crashed or was closed
                elif not self.is_vlc_running():
                    print("\n⚠ VLC was closed. Restarting playback...")
                    self.play_video(self.current_video)
                
                # Show status every 10 checks (30 seconds with 3 second interval)
                if int(time.time()) % 30 < self.check_interval:
                    video_count = len(self.get_video_files())
                    status = "Playing" if self.is_vlc_running() else "Stopped"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status} | "
                          f"Videos in folder: {video_count} | "
                          f"Current: {self.current_video.name if self.current_video else 'None'}")
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("MONITORING STOPPED BY USER")
            print("=" * 80)
            self.stop_vlc()
        
        except Exception as e:
            print(f"\n✗ Error in monitoring loop: {e}")
            self.stop_vlc()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Auto-play latest video in folder with VLC (infinite loop with monitoring)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vlc_auto_player.py
  python vlc_auto_player.py --folder "C:\\Users\\YourName\\Videos"
  python vlc_auto_player.py --folder "D:\\Movies" --check-interval 5

Features:
  - Automatically finds VLC installation
  - Plays latest video in infinite loop
  - Monitors folder for new videos
  - Switches to new video when detected
  - Restarts playback if VLC is closed
        """
    )
    
    parser.add_argument('--folder', type=str,
                       help='Folder path to monitor for videos (default: current directory)')
    parser.add_argument('--check-interval', type=int, default=3,
                       help='Seconds between folder checks (default: 3)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER")
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
    
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()

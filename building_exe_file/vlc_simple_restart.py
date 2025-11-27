"""
VLC Auto Video Player - Simple Restart Method (Most Reliable)
This is the simplest approach: restart VLC with the new video.
While it briefly closes and reopens VLC, it's the most reliable method.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required

Usage:
    python vlc_simple_restart.py
    python vlc_simple_restart.py --folder "C:\Videos" --check-interval 60
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
    
    def find_vlc(self) -> Optional[str]:
        """Find VLC installation path."""
        print("Searching for VLC Media Player...")
        print("-" * 80)
        
        # Check common paths
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', ''), 'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                print(f"✓ Found VLC at: {path}")
                return path
        
        # Check registry
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
                    return vlc_exe
            except:
                continue
        
        print("✗ VLC not found")
        return None


class SimpleVideoMonitor:
    """Simple video monitor using VLC restart method."""
    
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob'
    }
    
    def __init__(self, vlc_path: str, folder_path: str, check_interval: int = 60):
        self.vlc_path = vlc_path
        self.folder_path = Path(folder_path)
        self.check_interval = check_interval
        self.current_video = None
        self.vlc_process = None
        
        if not self.folder_path.exists():
            raise ValueError(f"Folder not found: {folder_path}")
        if not self.folder_path.is_dir():
            raise ValueError(f"Not a directory: {folder_path}")
    
    def get_video_files(self) -> List[Path]:
        """Get all video files in folder."""
        videos = []
        try:
            for file in self.folder_path.iterdir():
                if file.is_file() and file.suffix.lower() in self.VIDEO_EXTENSIONS:
                    videos.append(file)
        except Exception as e:
            print(f"Error scanning folder: {e}")
        return videos
    
    def get_latest_video(self) -> Optional[Path]:
        """Get newest video by modification time."""
        videos = self.get_video_files()
        if not videos:
            return None
        videos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return videos[0]
    
    def is_vlc_running(self) -> bool:
        """Check if VLC is running."""
        return self.vlc_process and self.vlc_process.poll() is None
    
    def stop_vlc(self):
        """Stop VLC if running."""
        if self.vlc_process and self.is_vlc_running():
            try:
                self.vlc_process.terminate()
                self.vlc_process.wait(timeout=2)
            except:
                try:
                    self.vlc_process.kill()
                    self.vlc_process.wait(timeout=1)
                except:
                    pass
        self.vlc_process = None
    
    def play_video(self, video_path: Path):
        """Start VLC with video in loop mode."""
        try:
            # Stop current VLC
            self.stop_vlc()
            
            # Brief pause for clean restart
            time.sleep(0.5)
            
            print(f"\n{'=' * 80}")
            print(f"▶️  Playing: {video_path.name}")
            print(f"   Location: {video_path}")
            print(f"   Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"   Modified: {datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}\n")
            
            # Start VLC with loop
            command = [
                self.vlc_path,
                str(video_path),
                '--loop',  # Loop current video
                '--no-video-title-show',  # Hide filename overlay
                '--play-and-exit',  # Exit when done (combined with loop, keeps running)
            ]
            
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.current_video = video_path
            print("✓ Playback started\n")
            
        except Exception as e:
            print(f"✗ Error playing video: {e}")
    
    def monitor_and_play(self):
        """Main monitoring loop."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Method: Restart VLC for new videos (simple & reliable)")
        print(f"Press Ctrl+C to stop")
        print("=" * 80)
        
        # Start with latest video
        latest = self.get_latest_video()
        if latest:
            print(f"\nFound {len(self.get_video_files())} video(s)")
            self.play_video(latest)
        else:
            print("\n⚠ No videos found. Waiting...")
        
        # Monitor loop
        try:
            last_status = time.time()
            
            while True:
                time.sleep(self.check_interval)
                
                # Check if VLC closed
                if self.current_video and not self.is_vlc_running():
                    print(f"\n⚠ VLC closed. Restarting playback...")
                    self.play_video(self.current_video)
                    continue
                
                # Check for new video
                latest = self.get_latest_video()
                
                if not latest:
                    if self.current_video:
                        print("\n⚠ No videos in folder")
                        self.stop_vlc()
                        self.current_video = None
                    continue
                
                # New video detected
                if not self.current_video or latest != self.current_video:
                    print(f"\n{'*' * 80}")
                    print("🎬 NEW VIDEO DETECTED!")
                    print(f"{'*' * 80}")
                    self.play_video(latest)
                    last_status = time.time()
                
                # Status update every 5 minutes
                if time.time() - last_status >= 300:
                    count = len(self.get_video_files())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Status: Playing '{self.current_video.name if self.current_video else 'None'}' | "
                          f"{count} video(s) in folder")
                    last_status = time.time()
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("STOPPED BY USER")
            print("=" * 80)
            self.stop_vlc()
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            self.stop_vlc()


def main():
    parser = argparse.ArgumentParser(
        description='Simple VLC auto-player (restart method - most reliable)',
        epilog="""
Examples:
  python vlc_simple_restart.py
  python vlc_simple_restart.py --folder "C:\\TVVideos" --check-interval 60

Note: This version restarts VLC when switching videos. It's simple but reliable.
        """
    )
    
    parser.add_argument('--folder', type=str,
                       help='Folder to monitor (default: current directory)')
    parser.add_argument('--check-interval', type=int, default=60,
                       help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER - Simple Restart Method")
    print("=" * 80)
    print()
    
    # Find VLC
    finder = VLCFinder()
    vlc_path = finder.find_vlc()
    
    if not vlc_path:
        print("\n❌ VLC not found. Please install from https://www.videolan.org/")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print()
    
    # Get folder
    folder = args.folder if args.folder else os.getcwd()
    if not args.folder:
        print(f"Using current directory: {folder}\n")
    
    # Run monitor
    try:
        monitor = SimpleVideoMonitor(vlc_path, folder, args.check_interval)
        monitor.monitor_and_play()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()

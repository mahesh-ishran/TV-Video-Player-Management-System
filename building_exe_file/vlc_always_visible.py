"""
VLC Auto Video Player - Always Visible (No Minimize)
This version ensures VLC window ALWAYS stays visible on screen.
Uses Windows API to force VLC window to stay in foreground.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required (uses ctypes for Windows API)

Usage:
    python vlc_always_visible.py --folder "C:\TVVideos" --check-interval 60
"""

import os
import sys
import time
import winreg
import subprocess
import argparse
import ctypes
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Windows API constants
SW_SHOW = 5
SW_RESTORE = 9
SW_SHOWNORMAL = 1
HWND_TOP = 0
SWP_SHOWWINDOW = 0x0040
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002


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


class WindowManager:
    """Class to manage Windows window state using Windows API."""
    
    def __init__(self):
        # Load Windows API functions
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
    
    def find_window_by_title_partial(self, partial_title: str) -> Optional[int]:
        """Find window handle by partial title match."""
        def enum_windows_callback(hwnd, results):
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                    if partial_title.lower() in title.lower():
                        results.append((hwnd, title))
            return True
        
        results = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.py_object)
        callback = callback_type(enum_windows_callback)
        self.user32.EnumWindows(callback, results)
        
        return results[0][0] if results else None
    
    def find_vlc_window(self) -> Optional[int]:
        """Find VLC window handle."""
        # Try different window title patterns
        patterns = ["VLC media player", "vlc.exe", "VLC"]
        
        for pattern in patterns:
            hwnd = self.find_window_by_title_partial(pattern)
            if hwnd:
                return hwnd
        
        return None
    
    def show_window(self, hwnd: int):
        """Show window (restore if minimized)."""
        self.user32.ShowWindow(hwnd, SW_RESTORE)
        self.user32.ShowWindow(hwnd, SW_SHOW)
    
    def bring_to_foreground(self, hwnd: int):
        """Bring window to foreground and make it topmost temporarily."""
        # Restore if minimized
        self.user32.ShowWindow(hwnd, SW_RESTORE)
        
        # Bring to front
        self.user32.SetForegroundWindow(hwnd)
        
        # Set as topmost temporarily to ensure visibility
        self.user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
    
    def ensure_window_visible(self, hwnd: int):
        """Ensure window is visible and not minimized."""
        # Check if minimized
        placement = self.get_window_placement(hwnd)
        if placement == 2:  # SW_SHOWMINIMIZED
            self.user32.ShowWindow(hwnd, SW_RESTORE)
        
        # Make sure it's visible
        self.user32.ShowWindow(hwnd, SW_SHOWNORMAL)
        self.user32.SetForegroundWindow(hwnd)
    
    def get_window_placement(self, hwnd: int) -> int:
        """Get window show state."""
        class WINDOWPLACEMENT(ctypes.Structure):
            _fields_ = [
                ('length', ctypes.c_uint),
                ('flags', ctypes.c_uint),
                ('showCmd', ctypes.c_uint),
                ('ptMinPosition', ctypes.c_long * 2),
                ('ptMaxPosition', ctypes.c_long * 2),
                ('rcNormalPosition', ctypes.c_long * 4),
            ]
        
        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        self.user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
        return placement.showCmd


class VideoMonitor:
    """Video monitor with window management."""
    
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
        self.window_manager = WindowManager()
        
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
    
    def ensure_vlc_visible(self):
        """Ensure VLC window is visible and not minimized."""
        try:
            # Try to find VLC window multiple times
            for attempt in range(5):
                hwnd = self.window_manager.find_vlc_window()
                if hwnd:
                    self.window_manager.bring_to_foreground(hwnd)
                    print(f"✓ VLC window brought to foreground")
                    return True
                time.sleep(0.5)
            
            print("⚠ Could not find VLC window (may still be starting)")
            return False
        except Exception as e:
            print(f"⚠ Error managing window: {e}")
            return False
    
    def play_video(self, video_path: Path):
        """Start VLC with video in loop mode, always visible."""
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
            
            # Start VLC with explicit window state
            command = [
                self.vlc_path,
                str(video_path),
                '--loop',  # Loop current video
                '--no-video-title-show',  # Hide filename overlay
            ]
            
            # Start process with NORMAL window state
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_SHOWNORMAL
            
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )
            
            # Wait for VLC to start and find its window
            print("Starting VLC...")
            time.sleep(2)
            
            # Ensure window is visible
            self.ensure_vlc_visible()
            
            self.current_video = video_path
            print("✓ Playback started (window visible)\n")
            
        except Exception as e:
            print(f"✗ Error playing video: {e}")
            import traceback
            traceback.print_exc()
    
    def check_and_restore_window(self):
        """Periodically check if VLC window got minimized and restore it."""
        try:
            hwnd = self.window_manager.find_vlc_window()
            if hwnd:
                placement = self.window_manager.get_window_placement(hwnd)
                if placement == 2:  # Minimized
                    print("⚠ VLC was minimized, restoring...")
                    self.window_manager.ensure_window_visible(hwnd)
        except:
            pass
    
    def monitor_and_play(self):
        """Main monitoring loop."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED (Always Visible Mode)")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"VLC will ALWAYS stay visible on screen")
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
            check_counter = 0
            
            while True:
                time.sleep(min(5, self.check_interval))  # Check every 5 seconds minimum
                check_counter += 1
                
                # Every 5 seconds, check if window got minimized
                self.check_and_restore_window()
                
                # Only check for new videos at the specified interval
                if check_counter * 5 < self.check_interval:
                    continue
                
                check_counter = 0
                
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
        description='VLC auto-player that keeps VLC always visible (never minimized)',
        epilog="""
Examples:
  python vlc_always_visible.py --folder "C:\\TVVideos"
  python vlc_always_visible.py --folder "C:\\TVVideos" --check-interval 60

Features:
  - VLC window ALWAYS stays visible on screen
  - Automatically restores if minimized
  - Monitors for new videos
  - Loops current video infinitely
        """
    )
    
    parser.add_argument('--folder', type=str,
                       help='Folder to monitor (default: current directory)')
    parser.add_argument('--check-interval', type=int, default=60,
                       help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER - Always Visible Mode")
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
        monitor = VideoMonitor(vlc_path, folder, args.check_interval)
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

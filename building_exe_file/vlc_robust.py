"""
VLC Auto Video Player - ROBUST VERSION
Combines comprehensive VLC detection (registry scan) with always-visible window management.
This version will find VLC on ANY Windows PC where it's installed.

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python vlc_robust.py --folder "C:\TVVideos" --check-interval 60
"""

import os
import sys
import time
import winreg
import subprocess
import argparse
import ctypes
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Windows API constants
SW_SHOW = 5
SW_RESTORE = 9
SW_SHOWNORMAL = 1
HWND_TOP = 0
SWP_SHOWWINDOW = 0x0040
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002


class RobustVLCFinder:
    """Comprehensive VLC finder using multiple methods including full registry scan."""
    
    def __init__(self):
        self.vlc_path = None
        # All registry paths where programs are listed
        self.registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
        ]
    
    def get_registry_value(self, key, value_name: str) -> Optional[str]:
        """Safely get a registry value."""
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value else None
        except FileNotFoundError:
            return None
        except Exception:
            return None
    
    def scan_registry_for_vlc(self) -> Optional[str]:
        """Scan Windows Registry comprehensively for VLC installation."""
        print("  → Scanning Windows Registry for VLC...")
        
        for hkey, path in self.registry_paths:
            try:
                reg_key = winreg.OpenKey(hkey, path)
                
                # For direct VLC registry path
                if "VideoLAN\\VLC" in path:
                    install_dir = self.get_registry_value(reg_key, "InstallDir")
                    reg_key.Close()
                    
                    if install_dir:
                        vlc_exe = os.path.join(install_dir, "vlc.exe")
                        if os.path.exists(vlc_exe):
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
                                # Look for vlc.exe in install location
                                vlc_exe = os.path.join(install_location, "vlc.exe")
                                if os.path.exists(vlc_exe):
                                    subkey.Close()
                                    reg_key.Close()
                                    return vlc_exe
                            
                            # Try DisplayIcon
                            display_icon = self.get_registry_value(subkey, "DisplayIcon")
                            if display_icon and "vlc.exe" in display_icon.lower():
                                # Extract path from icon string
                                icon_path = display_icon.split(",")[0].strip('"')
                                if os.path.exists(icon_path) and icon_path.lower().endswith("vlc.exe"):
                                    subkey.Close()
                                    reg_key.Close()
                                    return icon_path
                            
                            # Try UninstallString
                            uninstall_string = self.get_registry_value(subkey, "UninstallString")
                            if uninstall_string:
                                # Often contains path to uninstaller in VLC directory
                                uninstall_dir = os.path.dirname(uninstall_string.strip('"'))
                                vlc_exe = os.path.join(uninstall_dir, "vlc.exe")
                                if os.path.exists(vlc_exe):
                                    subkey.Close()
                                    reg_key.Close()
                                    return vlc_exe
                        
                        subkey.Close()
                    except OSError:
                        continue
                
                reg_key.Close()
            
            except FileNotFoundError:
                continue
            except PermissionError:
                continue
            except Exception:
                continue
        
        return None
    
    def check_common_paths(self) -> Optional[str]:
        """Check common VLC installation paths."""
        print("  → Checking common installation paths...")
        
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def check_path_environment(self) -> Optional[str]:
        """Check if VLC is in system PATH."""
        print("  → Checking system PATH...")
        
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for path_dir in path_dirs:
            vlc_exe = os.path.join(path_dir, 'vlc.exe')
            if os.path.exists(vlc_exe):
                return vlc_exe
        
        return None
    
    def search_program_files(self) -> Optional[str]:
        """Search Program Files directories for VLC."""
        print("  → Searching Program Files directories...")
        
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
                                        return vlc_exe
            except (PermissionError, OSError):
                continue
        
        return None
    
    def find_vlc(self) -> Optional[str]:
        """Find VLC using all available methods."""
        print("\n" + "=" * 80)
        print("SEARCHING FOR VLC MEDIA PLAYER")
        print("=" * 80)
        
        # Method 1: Check common paths (fastest)
        vlc_path = self.check_common_paths()
        if vlc_path:
            print(f"✓ Found VLC at: {vlc_path}")
            print(f"  Method: Common installation path")
            self.vlc_path = vlc_path
            return vlc_path
        
        # Method 2: Scan Windows Registry (most reliable)
        vlc_path = self.scan_registry_for_vlc()
        if vlc_path:
            print(f"✓ Found VLC at: {vlc_path}")
            print(f"  Method: Windows Registry")
            self.vlc_path = vlc_path
            return vlc_path
        
        # Method 3: Check PATH environment
        vlc_path = self.check_path_environment()
        if vlc_path:
            print(f"✓ Found VLC at: {vlc_path}")
            print(f"  Method: System PATH")
            self.vlc_path = vlc_path
            return vlc_path
        
        # Method 4: Search Program Files (thorough but slower)
        vlc_path = self.search_program_files()
        if vlc_path:
            print(f"✓ Found VLC at: {vlc_path}")
            print(f"  Method: Program Files search")
            self.vlc_path = vlc_path
            return vlc_path
        
        print("✗ VLC Media Player not found on this system")
        print("\nSearched locations:")
        print("  • Common installation paths")
        print("  • Windows Registry (all uninstall entries)")
        print("  • System PATH environment variable")
        print("  • Program Files directories")
        return None


class WindowManager:
    """Class to manage Windows window state using Windows API."""
    
    def __init__(self):
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
        patterns = ["VLC media player", "vlc.exe", "VLC"]
        
        for pattern in patterns:
            hwnd = self.find_window_by_title_partial(pattern)
            if hwnd:
                return hwnd
        
        return None
    
    def bring_to_foreground(self, hwnd: int):
        """Bring window to foreground and make it visible."""
        self.user32.ShowWindow(hwnd, SW_RESTORE)
        self.user32.SetForegroundWindow(hwnd)
        self.user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
    
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
    """Video monitor with robust VLC detection and window management."""
    
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob',
        '.mp3', '.wav', '.flac', '.aac'  # Added audio formats
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
    
    def ensure_vlc_visible(self) -> bool:
        """Ensure VLC window is visible and not minimized."""
        try:
            for attempt in range(5):
                hwnd = self.window_manager.find_vlc_window()
                if hwnd:
                    self.window_manager.bring_to_foreground(hwnd)
                    return True
                time.sleep(0.5)
            return False
        except Exception as e:
            print(f"⚠ Error managing window: {e}")
            return False
    
    def play_video(self, video_path: Path):
        """Start VLC with video in loop mode, always visible."""
        try:
            # Stop current VLC
            self.stop_vlc()
            time.sleep(0.5)
            
            print(f"\n{'=' * 80}")
            print(f"▶️  Playing: {video_path.name}")
            print(f"   Location: {video_path}")
            print(f"   Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
            print(f"   Modified: {datetime.fromtimestamp(video_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}\n")
            
            # Start VLC
            command = [
                self.vlc_path,
                str(video_path),
                '--loop',
                '--no-video-title-show',
            ]
            
            # Start with normal window state
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_SHOWNORMAL
            
            self.vlc_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )
            
            # Wait and ensure window is visible
            print("Starting VLC...")
            time.sleep(2)
            
            if self.ensure_vlc_visible():
                print("✓ VLC window is visible and in foreground\n")
            else:
                print("⚠ VLC started but window may not be visible\n")
            
            self.current_video = video_path
            
        except Exception as e:
            print(f"✗ Error playing video: {e}")
            import traceback
            traceback.print_exc()
    
    def check_and_restore_window(self):
        """Check if VLC window got minimized and restore it."""
        try:
            hwnd = self.window_manager.find_vlc_window()
            if hwnd:
                placement = self.window_manager.get_window_placement(hwnd)
                if placement == 2:  # Minimized
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ VLC was minimized, restoring...")
                    self.window_manager.bring_to_foreground(hwnd)
        except:
            pass
    
    def monitor_and_play(self):
        """Main monitoring loop."""
        print("\n" + "=" * 80)
        print("VIDEO MONITORING STARTED")
        print("=" * 80)
        print(f"Folder: {self.folder_path}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Window monitor: Every 5 seconds")
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
                time.sleep(5)  # Check every 5 seconds
                check_counter += 1
                
                # Check window state every 5 seconds
                self.check_and_restore_window()
                
                # Check for new videos at specified interval
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
                
                # Status update
                if time.time() - last_status >= 300:
                    count = len(self.get_video_files())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Playing: '{self.current_video.name if self.current_video else 'None'}' | "
                          f"Videos: {count}")
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
        description='Robust VLC auto-player with comprehensive VLC detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vlc_robust.py --folder "C:\\TVVideos"
  python vlc_robust.py --folder "C:\\TVVideos" --check-interval 60

Features:
  - ROBUST VLC detection (works on all PCs)
  - Scans Windows Registry like "Programs and Features"
  - VLC window ALWAYS stays visible
  - Monitors for new videos
  - Loops videos infinitely
        """
    )
    
    parser.add_argument('--folder', type=str, required=True,
                       help='Folder to monitor for videos')
    parser.add_argument('--check-interval', type=int, default=60,
                       help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("VLC AUTO VIDEO PLAYER - ROBUST VERSION")
    print("=" * 80)
    
    # Find VLC using comprehensive method
    finder = RobustVLCFinder()
    vlc_path = finder.find_vlc()
    
    if not vlc_path:
        print("\n" + "=" * 80)
        print("❌ VLC MEDIA PLAYER NOT FOUND")
        print("=" * 80)
        print("\nPlease install VLC Media Player:")
        print("  1. Download from: https://www.videolan.org/vlc/")
        print("  2. Install using default settings")
        print("  3. Run this script again")
        print("\nIf VLC is already installed but not detected:")
        print("  • Make sure it's properly installed (not just extracted)")
        print("  • Try reinstalling VLC")
        print("  • Check if VLC appears in Windows 'Programs and Features'")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("=" * 80)
    print()
    
    # Run monitor
    try:
        monitor = VideoMonitor(vlc_path, args.folder, args.check_interval)
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
    
    print("\nMonitoring stopped.")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

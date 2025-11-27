"""
VLC Playlist Functionality Tester
==================================
This script demonstrates how VLC playlists work for infinite looping.

Features:
- Finds VLC automatically on Windows
- Scans a folder for video files
- Creates M3U8 playlists
- Tests single video looping
- Tests multiple video looping
- Lots of print statements to understand the process

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+

Usage:
    python vlc_playlist_tester.py --folder "C:\Videos"
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List

# Supported video formats
VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob'
}


class VLCFinder:
    """Find VLC Media Player on Windows"""
    
    def __init__(self):
        self.vlc_path = None
    
    def check_common_paths(self) -> Optional[str]:
        """Check common VLC installation paths"""
        print("\n🔍 Checking common VLC installation paths...")
        
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 
                        'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 
                        'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for i, path in enumerate(common_paths, 1):
            print(f"   [{i}] Checking: {path}")
            if os.path.exists(path):
                print(f"   ✅ FOUND!")
                return path
            print(f"   ❌ Not here")
        
        return None
    
    def scan_registry_for_vlc(self) -> Optional[str]:
        """Scan Windows Registry for VLC"""
        print("\n🔍 Scanning Windows Registry...")
        
        try:
            import winreg
            
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
            ]
            
            for i, (hkey, path) in enumerate(registry_paths, 1):
                try:
                    print(f"   [{i}] Checking registry: {path}")
                    reg_key = winreg.OpenKey(hkey, path)
                    install_dir, _ = winreg.QueryValueEx(reg_key, "InstallDir")
                    winreg.CloseKey(reg_key)
                    
                    if install_dir:
                        vlc_exe = os.path.join(install_dir, "vlc.exe")
                        print(f"       Found install dir: {install_dir}")
                        if os.path.exists(vlc_exe):
                            print(f"   ✅ FOUND: {vlc_exe}")
                            return vlc_exe
                        print(f"   ❌ vlc.exe not in install dir")
                except FileNotFoundError:
                    print(f"   ❌ Registry key not found")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
        except ImportError:
            print("   ❌ winreg module not available (not Windows?)")
        except Exception as e:
            print(f"   ❌ Registry scan error: {e}")
        
        return None
    
    def find_vlc(self) -> Optional[str]:
        """Find VLC using all methods"""
        print("\n" + "="*70)
        print("🎯 SEARCHING FOR VLC MEDIA PLAYER")
        print("="*70)
        
        # Method 1: Common paths
        vlc_path = self.check_common_paths()
        if vlc_path:
            self.vlc_path = vlc_path
            return vlc_path
        
        # Method 2: Registry
        if sys.platform == 'win32':
            vlc_path = self.scan_registry_for_vlc()
            if vlc_path:
                self.vlc_path = vlc_path
                return vlc_path
        
        print("\n❌ VLC Media Player not found!")
        print("   Please install VLC from: https://www.videolan.org/vlc/")
        return None


class PlaylistTester:
    """Test VLC playlist functionality"""
    
    def __init__(self, vlc_path: str, folder_path: str):
        self.vlc_path = vlc_path
        self.folder_path = Path(folder_path)
        self.test_folder = Path(folder_path) / "playlist_test"
        
        print(f"\n📁 Test folder will be: {self.test_folder}")
        
    def get_video_files(self) -> List[Path]:
        """Find all video files in folder"""
        print(f"\n🔍 Scanning folder for videos: {self.folder_path}")
        
        videos = []
        try:
            for file in self.folder_path.iterdir():
                if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
                    videos.append(file)
                    print(f"   ✅ Found: {file.name}")
        except Exception as e:
            print(f"   ❌ Error scanning folder: {e}")
        
        print(f"\n📊 Total videos found: {len(videos)}")
        return videos
    
    def create_single_video_playlist(self, video_path: Path) -> Optional[Path]:
        """Create playlist with ONE video for infinite looping"""
        print("\n" + "="*70)
        print("📝 CREATING SINGLE VIDEO PLAYLIST")
        print("="*70)
        
        try:
            # Create test folder
            self.test_folder.mkdir(parents=True, exist_ok=True)
            print(f"✅ Test folder created: {self.test_folder}")
            
            # Playlist file path
            playlist_path = self.test_folder / "single_video_loop.m3u8"
            print(f"📄 Playlist file: {playlist_path}")
            
            print("\n📝 Writing playlist content...")
            print("   Line 1: #EXTM3U (Header)")
            print(f"   Line 2: #EXTINF:-1,{video_path.name} (Metadata)")
            print(f"   Line 3: {video_path} (Video path)")
            
            # Write playlist
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write(f"#EXTINF:-1,{video_path.name}\n")
                f.write(f"{video_path}\n")
            
            print(f"\n✅ Playlist created successfully!")
            
            # Show file contents
            print("\n" + "-"*70)
            print("📄 PLAYLIST FILE CONTENTS:")
            print("-"*70)
            with open(playlist_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
            print("-"*70)
            
            return playlist_path
            
        except Exception as e:
            print(f"\n❌ Error creating playlist: {e}")
            return None
    
    def create_multiple_video_playlist(self, video_paths: List[Path]) -> Optional[Path]:
        """Create playlist with MULTIPLE videos"""
        print("\n" + "="*70)
        print("📝 CREATING MULTIPLE VIDEO PLAYLIST")
        print("="*70)
        
        try:
            # Create test folder
            self.test_folder.mkdir(parents=True, exist_ok=True)
            
            # Playlist file path
            playlist_path = self.test_folder / "multiple_video_loop.m3u8"
            print(f"📄 Playlist file: {playlist_path}")
            
            print(f"\n📝 Adding {len(video_paths)} videos to playlist...")
            
            # Write playlist
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                print("   ✅ Wrote header: #EXTM3U")
                
                for i, video_path in enumerate(video_paths, 1):
                    print(f"   [{i}/{len(video_paths)}] Adding: {video_path.name}")
                    f.write(f"#EXTINF:-1,{video_path.name}\n")
                    f.write(f"{video_path}\n")
            
            print(f"\n✅ Playlist with {len(video_paths)} videos created!")
            
            # Show file contents
            print("\n" + "-"*70)
            print("📄 PLAYLIST FILE CONTENTS:")
            print("-"*70)
            with open(playlist_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
            print("-"*70)
            
            return playlist_path
            
        except Exception as e:
            print(f"\n❌ Error creating playlist: {e}")
            return None
    
    def play_playlist(self, playlist_path: Path, test_name: str):
        """Play a playlist with VLC"""
        print("\n" + "="*70)
        print(f"▶️  PLAYING: {test_name}")
        print("="*70)
        
        try:
            print(f"\n🎬 Starting VLC...")
            print(f"   VLC Path: {self.vlc_path}")
            print(f"   Playlist: {playlist_path}")
            
            # Build VLC command
            cmd = [
                self.vlc_path,
                str(playlist_path),
                '--loop',           # Loop the entire playlist
                '--repeat',         # Repeat current item
                '--fullscreen',     # Fullscreen mode
                '--no-video-title-show',  # Don't show title
            ]
            
            print(f"\n🔧 VLC Command:")
            for i, arg in enumerate(cmd):
                if i == 0:
                    print(f"   {arg}")
                else:
                    print(f"   {arg}")
            
            print(f"\n🚀 Launching VLC...")
            
            # Start VLC
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_SHOWNORMAL
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print(f"✅ VLC started! (PID: {process.pid})")
            print(f"\n🎯 What's happening:")
            print(f"   • VLC is playing the playlist")
            print(f"   • --loop makes it restart the playlist when finished")
            print(f"   • --repeat makes it repeat each video")
            print(f"   • Videos will play INFINITELY")
            
            print(f"\n⏱️  Video will play for 10 seconds (for testing)...")
            print(f"   Close VLC manually to test longer")
            
            # Wait a bit
            for i in range(10, 0, -1):
                print(f"   ⏳ {i} seconds remaining...", end='\r')
                time.sleep(1)
            
            print(f"\n\n🛑 Stopping VLC...")
            process.terminate()
            process.wait(timeout=3)
            print(f"✅ VLC stopped")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error playing playlist: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_tests(self):
        """Run all playlist tests"""
        print("\n" + "="*70)
        print("🧪 VLC PLAYLIST FUNCTIONALITY TESTER")
        print("="*70)
        
        # Get videos
        videos = self.get_video_files()
        
        if not videos:
            print("\n❌ No videos found in folder!")
            print(f"   Please add video files to: {self.folder_path}")
            return
        
        # Test 1: Single video infinite loop
        print("\n\n" + "🔵"*35)
        print("TEST 1: SINGLE VIDEO INFINITE LOOP")
        print("🔵"*35)
        
        playlist1 = self.create_single_video_playlist(videos[0])
        if playlist1:
            input("\n⏸️  Press Enter to start Test 1 (Single Video Loop)...")
            self.play_playlist(playlist1, "Single Video Loop")
        
        # Test 2: Multiple videos (if available)
        if len(videos) > 1:
            print("\n\n" + "🟢"*35)
            print("TEST 2: MULTIPLE VIDEO PLAYLIST LOOP")
            print("🟢"*35)
            
            # Use up to 3 videos for testing
            test_videos = videos[:min(3, len(videos))]
            playlist2 = self.create_multiple_video_playlist(test_videos)
            
            if playlist2:
                input("\n⏸️  Press Enter to start Test 2 (Multiple Videos Loop)...")
                self.play_playlist(playlist2, "Multiple Video Loop")
        else:
            print("\n⏭️  Skipping Test 2 (need at least 2 videos)")
        
        # Summary
        print("\n\n" + "="*70)
        print("✅ TESTING COMPLETE")
        print("="*70)
        print(f"\n📁 Test files saved in: {self.test_folder}")
        print(f"\n💡 Key Learnings:")
        print(f"   1. M3U8 playlists are simple text files")
        print(f"   2. #EXTM3U header identifies the format")
        print(f"   3. #EXTINF:-1,<name> provides metadata")
        print(f"   4. File paths follow metadata lines")
        print(f"   5. --loop + --repeat = infinite playback")
        print(f"   6. VLC handles the looping automatically")
        print(f"\n🎯 Use Case:")
        print(f"   This is perfect for TV displays, kiosks, or")
        print(f"   any scenario needing continuous video playback!")


def main():
    parser = argparse.ArgumentParser(
        description='Test VLC playlist functionality with detailed output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vlc_playlist_tester.py --folder "C:\\Videos"
  python vlc_playlist_tester.py --folder "C:\\TVVideos"

What this script does:
  1. Finds VLC on your system
  2. Scans your folder for video files
  3. Creates M3U8 playlist files
  4. Tests single video looping
  5. Tests multiple video looping
  6. Shows detailed output at every step
        """
    )
    
    parser.add_argument('--folder', type=str, required=True,
                       help='Folder containing video files to test')
    
    args = parser.parse_args()
    
    # Find VLC
    finder = VLCFinder()
    vlc_path = finder.find_vlc()
    
    if not vlc_path:
        print("\n" + "="*70)
        print("❌ CANNOT PROCEED WITHOUT VLC")
        print("="*70)
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("\n" + "="*70)
    print(f"✅ VLC Found: {vlc_path}")
    print("="*70)
    
    # Check folder
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"\n❌ Folder not found: {folder_path}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"\n❌ Not a directory: {folder_path}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print(f"✅ Folder exists: {folder_path}")
    
    # Run tests
    try:
        tester = PlaylistTester(vlc_path, args.folder)
        tester.run_tests()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

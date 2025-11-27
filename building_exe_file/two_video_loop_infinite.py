"""
Two Video Infinite Loop Player
================================
Plays TWO videos from a folder in sequence, looping indefinitely.

Sequence: Video1 → Video2 → Video1 → Video2 → ... (forever)

Requirements:
    - Windows OS
    - VLC Media Player installed
    - Python 3.6+
    - At least 2 video files in the folder

Usage:
    python two_video_loop.py --folder "C:\Videos"
"""

import os
import sys
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
    
    def check_common_paths(self) -> Optional[str]:
        """Check common VLC installation paths"""
        print("🔍 Searching for VLC Media Player...")
        
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 
                        'VideoLAN', 'VLC', 'vlc.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 
                        'VideoLAN', 'VLC', 'vlc.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                print(f"✅ Found VLC: {path}\n")
                return path
        
        return None
    
    def scan_registry_for_vlc(self) -> Optional[str]:
        """Scan Windows Registry for VLC"""
        try:
            import winreg
            
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VideoLAN\VLC"),
            ]
            
            for hkey, path in registry_paths:
                try:
                    reg_key = winreg.OpenKey(hkey, path)
                    install_dir, _ = winreg.QueryValueEx(reg_key, "InstallDir")
                    winreg.CloseKey(reg_key)
                    
                    if install_dir:
                        vlc_exe = os.path.join(install_dir, "vlc.exe")
                        if os.path.exists(vlc_exe):
                            print(f"✅ Found VLC: {vlc_exe}\n")
                            return vlc_exe
                except:
                    continue
            
        except:
            pass
        
        return None
    
    def find_vlc(self) -> Optional[str]:
        """Find VLC using all methods"""
        vlc_path = self.check_common_paths()
        if vlc_path:
            return vlc_path
        
        if sys.platform == 'win32':
            vlc_path = self.scan_registry_for_vlc()
            if vlc_path:
                return vlc_path
        
        print("❌ VLC Media Player not found!")
        print("   Please install VLC from: https://www.videolan.org/vlc/")
        return None


def get_video_files(folder_path: Path) -> List[Path]:
    """Get all video files from folder"""
    print(f"📁 Scanning folder: {folder_path}\n")
    
    videos = []
    try:
        for file in folder_path.iterdir():
            if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(file)
                print(f"   ✅ Found: {file.name}")
    except Exception as e:
        print(f"   ❌ Error scanning folder: {e}")
        return []
    
    # Sort by name for consistent order
    videos.sort(key=lambda x: x.name)
    
    print(f"\n📊 Total videos found: {len(videos)}")
    return videos


def create_two_video_playlist(video1: Path, video2: Path, output_folder: Path) -> Optional[Path]:
    """Create playlist with two videos for infinite looping"""
    print("\n" + "="*70)
    print("📝 CREATING TWO-VIDEO PLAYLIST")
    print("="*70)
    
    try:
        # Ensure output folder exists
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Playlist file path
        playlist_path = output_folder / "two_video_loop.m3u8"
        
        print(f"\n📄 Playlist file: {playlist_path}")
        print(f"\n📝 Adding videos to playlist:")
        print(f"   [1] {video1.name}")
        print(f"   [2] {video2.name}")
        
        # Write playlist
        with open(playlist_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("#EXTM3U\n")
            
            # Video 1
            f.write(f"#EXTINF:-1,{video1.name}\n")
            f.write(f"{video1}\n")
            
            # Video 2
            f.write(f"#EXTINF:-1,{video2.name}\n")
            f.write(f"{video2}\n")
        
        print(f"\n✅ Playlist created successfully!")
        
        # Show file contents
        print("\n" + "-"*70)
        print("📄 PLAYLIST CONTENTS:")
        print("-"*70)
        with open(playlist_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
        print("-"*70)
        
        return playlist_path
        
    except Exception as e:
        print(f"\n❌ Error creating playlist: {e}")
        return None


def play_playlist_infinite(vlc_path: str, playlist_path: Path):
    """Play playlist in infinite loop"""
    print("\n" + "="*70)
    print("▶️  STARTING INFINITE PLAYBACK")
    print("="*70)
    
    try:
        print(f"\n🎬 Configuration:")
        print(f"   VLC Path: {vlc_path}")
        print(f"   Playlist: {playlist_path}")
        
        # Build VLC command
        cmd = [
            vlc_path,
            str(playlist_path),
            '--loop',                    # Loop entire playlist
            '--fullscreen',              # Play in fullscreen
            '--no-video-title-show',     # Don't show video title
            '--no-osd',                  # No on-screen display
            '--video-on-top',            # Keep window on top
        ]
        
        print(f"\n🔧 VLC Command:")
        for arg in cmd:
            print(f"   {arg}")
        
        print(f"\n🚀 Starting VLC...")
        print(f"\n🔄 Playback Sequence:")
        print(f"   Video 1 → Video 2 → Video 1 → Video 2 → ... (infinite loop)")
        
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
        
        print(f"\n✅ VLC Started! (PID: {process.pid})")
        print(f"\n" + "="*70)
        print("🎯 PLAYBACK IN PROGRESS")
        print("="*70)
        print(f"\n💡 What's happening:")
        print(f"   • Two videos are playing in sequence")
        print(f"   • When Video 2 ends, it goes back to Video 1")
        print(f"   • This will continue FOREVER (until you close VLC)")
        print(f"   • Press Alt+F4 or close VLC window to stop")
        print(f"\n⌨️  Press Ctrl+C in this terminal to exit (VLC will keep playing)")
        
        # Wait for VLC to finish (it won't, because of infinite loop)
        try:
            process.wait()
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Terminal interrupted - VLC is still playing")
            print(f"   Close VLC window manually to stop playback")
        
    except Exception as e:
        print(f"\n❌ Error starting VLC: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description='Play two videos in sequence infinitely',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python two_video_loop.py --folder "C:\\Videos"
  python two_video_loop.py --folder "C:\\TVVideos"

What this does:
  1. Finds the first TWO videos in your folder
  2. Creates a playlist: Video1 → Video2
  3. Plays them in infinite loop
  
Sequence:
  Video1 plays → Video2 plays → Video1 plays → Video2 plays → ...
        """
    )
    
    parser.add_argument('--folder', type=str, required=True,
                       help='Folder containing video files')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🎬 TWO VIDEO INFINITE LOOP PLAYER")
    print("="*70)
    print()
    
    # Check folder exists
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"❌ Not a directory: {folder_path}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Find VLC
    finder = VLCFinder()
    vlc_path = finder.find_vlc()
    
    if not vlc_path:
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Get video files
    videos = get_video_files(folder_path)
    
    if len(videos) < 2:
        print(f"\n❌ Need at least 2 videos, found only {len(videos)}")
        print(f"   Please add more video files to: {folder_path}")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Select first two videos
    video1 = videos[0]
    video2 = videos[1]
    
    print(f"\n🎯 Selected videos:")
    print(f"   [1] {video1.name}")
    print(f"   [2] {video2.name}")
    
    if len(videos) > 2:
        print(f"\n📌 Note: Found {len(videos)} videos, using first 2")
        print(f"   Ignored videos:")
        for i, v in enumerate(videos[2:], 3):
            print(f"   [{i}] {v.name}")
    
    # Create playlist
    playlist_path = create_two_video_playlist(video1, video2, folder_path)
    
    if not playlist_path:
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Ask user to confirm
    print(f"\n" + "="*70)
    input("⏸️  Press Enter to start playback...")
    
    # Play
    play_playlist_infinite(vlc_path, playlist_path)
    
    print(f"\n✅ Done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

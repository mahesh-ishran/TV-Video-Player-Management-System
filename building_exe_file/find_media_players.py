"""
Windows Media Player Finder
This script finds and lists all media player applications installed on a Windows PC.

Requirements:
    - Windows OS
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python find_media_players.py
"""

import os
import winreg
import platform
from pathlib import Path
from typing import List, Dict, Set

class MediaPlayerFinder:
    def __init__(self):
        # Common media player executables to search for
        self.media_players = {
            'VLC Media Player': ['vlc.exe'],
            'Windows Media Player': ['wmplayer.exe'],
            'Groove Music': ['GrooveMusic.exe'],
            'Media Player Classic': ['mpc-hc.exe', 'mpc-hc64.exe', 'mpc-be.exe', 'mpc-be64.exe'],
            'PotPlayer': ['PotPlayerMini.exe', 'PotPlayerMini64.exe', 'PotPlayer.exe', 'PotPlayer64.exe'],
            'KMPlayer': ['KMPlayer.exe', 'KMPlayer64.exe'],
            'GOM Player': ['GOM.exe', 'GOMPlayer.exe'],
            'DivX Player': ['DivXPlayer.exe'],
            'RealPlayer': ['RealPlay.exe'],
            'Kodi': ['kodi.exe'],
            'Plex': ['Plex.exe', 'PlexMediaPlayer.exe'],
            'iTunes': ['iTunes.exe'],
            'Spotify': ['Spotify.exe'],
            'Winamp': ['winamp.exe'],
            'AIMP': ['AIMP.exe'],
            'foobar2000': ['foobar2000.exe'],
            'MusicBee': ['MusicBee.exe'],
            'MediaMonkey': ['MediaMonkey.exe'],
            'JRiver Media Center': ['Media Center.exe'],
            'PowerDVD': ['PowerDVD.exe'],
            'Zoom Player': ['zplayer.exe'],
            'SMPlayer': ['smplayer.exe'],
            'MPV': ['mpv.exe'],
            'QuickTime Player': ['QuickTimePlayer.exe'],
            'ACG Player': ['ACGPlayer.View.exe'],
            '5KPlayer': ['5KPlayer.exe'],
            'Clementine': ['clementine.exe'],
            'Audacious': ['audacious.exe'],
        }
        
        self.found_players = {}
        
    def check_common_directories(self) -> Dict[str, str]:
        """Check common installation directories for media players."""
        found = {}
        
        # Common installation directories
        search_paths = [
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        ]
        
        print("Searching common installation directories...")
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
                
            for player_name, executables in self.media_players.items():
                if player_name in found:
                    continue
                    
                try:
                    for root, dirs, files in os.walk(search_path):
                        # Limit depth to avoid very deep searches
                        depth = root[len(search_path):].count(os.sep)
                        if depth > 3:
                            continue
                            
                        for exe in executables:
                            if exe.lower() in [f.lower() for f in files]:
                                full_path = os.path.join(root, exe)
                                found[player_name] = full_path
                                break
                        
                        if player_name in found:
                            break
                            
                except (PermissionError, OSError):
                    continue
        
        return found
    
    def check_registry(self) -> Dict[str, str]:
        """Check Windows Registry for installed media players."""
        found = {}
        
        print("Searching Windows Registry...")
        
        # Registry paths to check
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        for hkey, reg_path in registry_paths:
            try:
                reg_key = winreg.OpenKey(hkey, reg_path)
                
                for i in range(winreg.QueryInfoKey(reg_key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(reg_key, i)
                        subkey = winreg.OpenKey(reg_key, subkey_name)
                        
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            install_location = None
                            
                            try:
                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except FileNotFoundError:
                                pass
                            
                            # Check if this is a media player we're looking for
                            for player_name, executables in self.media_players.items():
                                if player_name.lower() in display_name.lower():
                                    if install_location and os.path.exists(install_location):
                                        # Try to find the executable
                                        for exe in executables:
                                            exe_path = os.path.join(install_location, exe)
                                            if os.path.exists(exe_path):
                                                found[player_name] = exe_path
                                                break
                                    elif player_name not in found:
                                        found[player_name] = display_name
                        
                        except FileNotFoundError:
                            pass
                        finally:
                            subkey.Close()
                    
                    except OSError:
                        continue
                
                reg_key.Close()
            
            except FileNotFoundError:
                continue
            except PermissionError:
                continue
        
        return found
    
    def check_environment_path(self) -> Dict[str, str]:
        """Check if media players are in the system PATH."""
        found = {}
        
        print("Searching system PATH...")
        
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        
        for path_dir in path_dirs:
            if not os.path.exists(path_dir):
                continue
            
            try:
                for player_name, executables in self.media_players.items():
                    if player_name in found:
                        continue
                    
                    for exe in executables:
                        exe_path = os.path.join(path_dir, exe)
                        if os.path.exists(exe_path):
                            found[player_name] = exe_path
                            break
            
            except (PermissionError, OSError):
                continue
        
        return found
    
    def find_all_media_players(self) -> Dict[str, str]:
        """Find all media players using multiple methods."""
        print("=" * 80)
        print("WINDOWS MEDIA PLAYER FINDER")
        print("=" * 80)
        print()
        
        # Check OS
        if platform.system() != 'Windows':
            print(f"Warning: This script is designed for Windows. Current OS: {platform.system()}")
            print()
        
        all_found = {}
        
        # Method 1: Check common directories
        print("\n[1] Checking common installation directories...")
        print("-" * 80)
        directory_found = self.check_common_directories()
        all_found.update(directory_found)
        
        # Method 2: Check registry
        print("\n[2] Checking Windows Registry...")
        print("-" * 80)
        registry_found = self.check_registry()
        # Merge without overwriting existing found paths
        for name, path in registry_found.items():
            if name not in all_found:
                all_found[name] = path
        
        # Method 3: Check PATH
        print("\n[3] Checking system PATH...")
        print("-" * 80)
        path_found = self.check_environment_path()
        for name, path in path_found.items():
            if name not in all_found:
                all_found[name] = path
        
        return all_found
    
    def display_results(self, found_players: Dict[str, str]):
        """Display the found media players in a formatted way."""
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        if not found_players:
            print("No media players found on this system.")
            print()
            print("Possible reasons:")
            print("  - No media players are installed")
            print("  - Players are installed in non-standard locations")
            print("  - Insufficient permissions to access certain directories")
        else:
            print(f"Found {len(found_players)} media player(s):\n")
            
            for i, (player_name, player_path) in enumerate(sorted(found_players.items()), 1):
                print(f"{i}. {player_name}")
                
                # Check if path is executable or just a name
                if os.path.exists(str(player_path)) and os.path.isfile(str(player_path)):
                    print(f"   Location: {player_path}")
                    
                    # Get file size
                    try:
                        size_mb = os.path.getsize(player_path) / (1024 * 1024)
                        print(f"   Size: {size_mb:.2f} MB")
                    except:
                        pass
                else:
                    print(f"   Info: {player_path}")
                
                print()
        
        print("=" * 80)


def main():
    """Main function to run the media player finder."""
    finder = MediaPlayerFinder()
    
    try:
        found_players = finder.find_all_media_players()
        finder.display_results(found_players)
        
    except KeyboardInterrupt:
        print("\n\nSearch interrupted by user.")
    
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()

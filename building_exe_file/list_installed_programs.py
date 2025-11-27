"""
Windows Installed Programs Lister
This script lists all programs installed on Windows PC by reading the registry.
It extracts the same information shown in Control Panel > Programs and Features.

Requirements:
    - Windows OS
    - Python 3.6+
    - No additional packages required (uses only standard library)

Usage:
    python list_installed_programs.py
    python list_installed_programs.py --export csv
    python list_installed_programs.py --export json
"""

import winreg
import platform
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import argparse


class InstalledProgramsLister:
    def __init__(self):
        # Registry paths where installed programs are listed
        self.registry_paths = [
            # 64-bit programs on 64-bit Windows
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            # 32-bit programs on 64-bit Windows
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            # Current user programs
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        self.programs = []
    
    def parse_install_date(self, date_str: str) -> Optional[str]:
        """Convert YYYYMMDD format to readable date."""
        if not date_str or len(date_str) != 8:
            return None
        
        try:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y-%m-%d")
        except:
            return date_str
    
    def format_size(self, size_kb: int) -> str:
        """Convert size in KB to human-readable format."""
        try:
            size_kb = int(size_kb)
            if size_kb < 1024:
                return f"{size_kb} KB"
            elif size_kb < 1024 * 1024:
                return f"{size_kb / 1024:.2f} MB"
            else:
                return f"{size_kb / (1024 * 1024):.2f} GB"
        except:
            return "Unknown"
    
    def get_registry_value(self, key, value_name: str) -> Optional[str]:
        """Safely get a registry value."""
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value else None
        except FileNotFoundError:
            return None
        except Exception:
            return None
    
    def scan_registry_path(self, hkey, path: str) -> List[Dict]:
        """Scan a specific registry path for installed programs."""
        programs = []
        
        try:
            reg_key = winreg.OpenKey(hkey, path)
            num_subkeys = winreg.QueryInfoKey(reg_key)[0]
            
            for i in range(num_subkeys):
                try:
                    subkey_name = winreg.EnumKey(reg_key, i)
                    subkey = winreg.OpenKey(reg_key, subkey_name)
                    
                    # Get program information
                    display_name = self.get_registry_value(subkey, "DisplayName")
                    
                    # Skip if no display name (usually system components)
                    if not display_name:
                        subkey.Close()
                        continue
                    
                    # Skip Windows Update entries
                    if display_name.startswith("KB") or "Update for" in display_name:
                        subkey.Close()
                        continue
                    
                    program_info = {
                        'name': display_name,
                        'version': self.get_registry_value(subkey, "DisplayVersion"),
                        'publisher': self.get_registry_value(subkey, "Publisher"),
                        'install_date': self.parse_install_date(
                            self.get_registry_value(subkey, "InstallDate") or ""
                        ),
                        'install_location': self.get_registry_value(subkey, "InstallLocation"),
                        'uninstall_string': self.get_registry_value(subkey, "UninstallString"),
                        'size': self.get_registry_value(subkey, "EstimatedSize"),
                        'registry_key': subkey_name,
                    }
                    
                    # Format size if available
                    if program_info['size']:
                        program_info['size_formatted'] = self.format_size(program_info['size'])
                    else:
                        program_info['size_formatted'] = "Unknown"
                    
                    programs.append(program_info)
                    subkey.Close()
                
                except OSError:
                    continue
                except Exception as e:
                    continue
            
            reg_key.Close()
        
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"Permission denied accessing registry path: {path}")
        except Exception as e:
            print(f"Error accessing registry: {e}")
        
        return programs
    
    def get_all_programs(self) -> List[Dict]:
        """Get all installed programs from all registry locations."""
        print("=" * 100)
        print("SCANNING INSTALLED PROGRAMS")
        print("=" * 100)
        print()
        
        # Check OS
        if platform.system() != 'Windows':
            print(f"Warning: This script is designed for Windows. Current OS: {platform.system()}")
            return []
        
        all_programs = []
        seen_names = set()  # To avoid duplicates
        
        for i, (hkey, path) in enumerate(self.registry_paths, 1):
            hkey_name = "HKEY_LOCAL_MACHINE" if hkey == winreg.HKEY_LOCAL_MACHINE else "HKEY_CURRENT_USER"
            print(f"[{i}/{len(self.registry_paths)}] Scanning {hkey_name}\\{path}...")
            
            programs = self.scan_registry_path(hkey, path)
            
            # Add only unique programs (avoid duplicates)
            for program in programs:
                # Create a unique identifier
                identifier = f"{program['name']}_{program['version']}_{program['publisher']}"
                if identifier not in seen_names:
                    seen_names.add(identifier)
                    all_programs.append(program)
            
            print(f"   Found {len(programs)} entries ({len(all_programs)} unique total)")
        
        # Sort by name
        all_programs.sort(key=lambda x: x['name'].lower())
        
        self.programs = all_programs
        return all_programs
    
    def display_programs(self, programs: List[Dict], limit: Optional[int] = None):
        """Display programs in a formatted table."""
        print("\n" + "=" * 100)
        print("INSTALLED PROGRAMS")
        print("=" * 100)
        print()
        
        if not programs:
            print("No programs found.")
            return
        
        print(f"Total programs found: {len(programs)}\n")
        
        display_count = len(programs) if limit is None else min(limit, len(programs))
        
        for i, program in enumerate(programs[:display_count], 1):
            print(f"{i}. {program['name']}")
            
            if program['version']:
                print(f"   Version: {program['version']}")
            
            if program['publisher']:
                print(f"   Publisher: {program['publisher']}")
            
            if program['install_date']:
                print(f"   Install Date: {program['install_date']}")
            
            if program['size_formatted'] and program['size_formatted'] != "Unknown":
                print(f"   Size: {program['size_formatted']}")
            
            if program['install_location']:
                print(f"   Location: {program['install_location']}")
            
            print()
        
        if limit and len(programs) > limit:
            print(f"... and {len(programs) - limit} more programs")
            print("(Use --all flag to see all programs or export to file)")
        
        print("=" * 100)
    
    def export_to_csv(self, filename: str = "installed_programs.csv"):
        """Export programs list to CSV file."""
        if not self.programs:
            print("No programs to export.")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['name', 'version', 'publisher', 'install_date', 
                            'size_formatted', 'install_location']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                
                writer.writeheader()
                for program in self.programs:
                    writer.writerow(program)
            
            print(f"\n✓ Successfully exported {len(self.programs)} programs to: {filename}")
            return filename
        
        except Exception as e:
            print(f"\n✗ Error exporting to CSV: {e}")
            return None
    
    def export_to_json(self, filename: str = "installed_programs.json"):
        """Export programs list to JSON file."""
        if not self.programs:
            print("No programs to export.")
            return
        
        try:
            # Create a clean version without internal fields
            export_data = []
            for program in self.programs:
                clean_program = {
                    'name': program['name'],
                    'version': program['version'],
                    'publisher': program['publisher'],
                    'install_date': program['install_date'],
                    'size': program['size_formatted'],
                    'install_location': program['install_location'],
                }
                export_data.append(clean_program)
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Successfully exported {len(self.programs)} programs to: {filename}")
            return filename
        
        except Exception as e:
            print(f"\n✗ Error exporting to JSON: {e}")
            return None
    
    def export_to_text(self, filename: str = "installed_programs.txt"):
        """Export programs list to text file."""
        if not self.programs:
            print("No programs to export.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as txtfile:
                txtfile.write("=" * 100 + "\n")
                txtfile.write("INSTALLED PROGRAMS LIST\n")
                txtfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                txtfile.write(f"Total Programs: {len(self.programs)}\n")
                txtfile.write("=" * 100 + "\n\n")
                
                for i, program in enumerate(self.programs, 1):
                    txtfile.write(f"{i}. {program['name']}\n")
                    
                    if program['version']:
                        txtfile.write(f"   Version: {program['version']}\n")
                    
                    if program['publisher']:
                        txtfile.write(f"   Publisher: {program['publisher']}\n")
                    
                    if program['install_date']:
                        txtfile.write(f"   Install Date: {program['install_date']}\n")
                    
                    if program['size_formatted'] and program['size_formatted'] != "Unknown":
                        txtfile.write(f"   Size: {program['size_formatted']}\n")
                    
                    if program['install_location']:
                        txtfile.write(f"   Location: {program['install_location']}\n")
                    
                    txtfile.write("\n")
            
            print(f"\n✓ Successfully exported {len(self.programs)} programs to: {filename}")
            return filename
        
        except Exception as e:
            print(f"\n✗ Error exporting to text: {e}")
            return None


def main():
    """Main function with command-line argument support."""
    parser = argparse.ArgumentParser(
        description='List all installed programs on Windows PC',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python list_installed_programs.py                    # Display programs
  python list_installed_programs.py --all              # Display all programs
  python list_installed_programs.py --export csv       # Export to CSV
  python list_installed_programs.py --export json      # Export to JSON
  python list_installed_programs.py --export txt       # Export to text file
        """
    )
    
    parser.add_argument('--export', choices=['csv', 'json', 'txt'], 
                       help='Export programs to file format')
    parser.add_argument('--output', type=str, 
                       help='Output filename (default: installed_programs.[format])')
    parser.add_argument('--all', action='store_true',
                       help='Display all programs (default shows first 50)')
    
    args = parser.parse_args()
    
    # Create lister and scan
    lister = InstalledProgramsLister()
    
    try:
        programs = lister.get_all_programs()
        
        # Display results
        if not args.export:
            limit = None if args.all else 50
            lister.display_programs(programs, limit=limit)
        
        # Export if requested
        if args.export:
            output_file = args.output
            
            if args.export == 'csv':
                if not output_file:
                    output_file = 'installed_programs.csv'
                lister.export_to_csv(output_file)
                
            elif args.export == 'json':
                if not output_file:
                    output_file = 'installed_programs.json'
                lister.export_to_json(output_file)
                
            elif args.export == 'txt':
                if not output_file:
                    output_file = 'installed_programs.txt'
                lister.export_to_text(output_file)
    
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()

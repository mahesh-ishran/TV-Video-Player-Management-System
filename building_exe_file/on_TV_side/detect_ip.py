import socket
import requests

print("="*60)
print("     IP ADDRESS DETECTION TOOL")
print("="*60)
print()

# Get local IP
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Hostname: {hostname}")
    print(f"Local IP (from hostname): {local_ip}")
except Exception as e:
    print(f"Error getting local IP: {e}")
    local_ip = None

print()

# Get external IP
try:
    print("Checking external IP...")
    response = requests.get('https://api.ipify.org?format=text', timeout=10)
    external_ip = response.text.strip()
    print(f"External IP (public): {external_ip}")
except Exception as e:
    print(f"Could not get external IP: {e}")
    external_ip = None

print()
print("="*60)
print("RECOMMENDATION FOR VIDEO FILENAME:")
print("="*60)
print()

if local_ip:
    print(f"Option 1: {local_ip}.mp4")
    print(f"          (Use this if server sees itself as local IP)")
    print()

if external_ip:
    print(f"Option 2: {external_ip}.mp4")
    print(f"          (Use this if server sees itself as public IP)")
    print()

print("WHAT TO DO:")
print("1. Create BOTH video files with these names in Google Drive")
print("2. OR create just one and see which the main script looks for")
print()
print("="*60)

input("\nPress Enter to exit...")

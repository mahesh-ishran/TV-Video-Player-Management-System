# play_with_vlc.py
import os, sys, shutil, subprocess, argparse
from pathlib import Path

def find_vlc():
    """Return full path to vlc.exe (Windows) or 'vlc' (others), or None if not found."""
    candidates = []

    # 1) Optional env var
    env = os.environ.get("VLC_PATH")
    if env:
        candidates.append(Path(env))

    # 2) PATH
    which = shutil.which("vlc.exe" if os.name == "nt" else "vlc")
    if which:
        candidates.append(Path(which))

    # 3) Windows Registry + common locations
    if os.name == "nt":
        try:
            import winreg
            # App Paths entry (best bet)
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for sub in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\vlc.exe",
                            r"SOFTWARE\VideoLAN\VLC"):
                    try:
                        with winreg.OpenKey(root, sub) as key:
                            for valname in ("", "Path", "InstallDir"):
                                try:
                                    val, _ = winreg.QueryValueEx(key, valname)
                                    p = Path(val)
                                    if p.is_file() and p.name.lower() == "vlc.exe":
                                        candidates.append(p)
                                    else:
                                        vp = p / "vlc.exe"
                                        if vp.exists():
                                            candidates.append(vp)
                                except FileNotFoundError:
                                    pass
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

        # Common install dirs
        for base in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                     Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))):
            candidates.append(base / "VideoLAN" / "VLC" / "vlc.exe")
    else:
        # Typical Unix locations (in case you reuse on Linux/macOS)
        candidates += [Path("/usr/bin/vlc"), Path("/usr/local/bin/vlc")]

    # Return the first existing path
    for p in candidates:
        if p and Path(p).exists():
            return str(Path(p))
    return None

VIDEO_EXTS = {'.mp4','.mkv','.avi','.mov','.m4v','.webm','.ts','.mpeg','.mpg','.wmv'}

def pick_video(folder: Path, filename: str | None, index: int | None):
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")

    if filename:
        # Try exact then case-insensitive
        candidate = folder / filename
        if candidate.exists():
            return str(candidate)
        matches = [f for f in folder.iterdir() if f.is_file() and f.name.lower() == filename.lower()]
        if matches:
            return str(matches[0])
        raise FileNotFoundError(f"'{filename}' not found in {folder}")

    files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS])
    if not files:
        raise FileNotFoundError(f"No video files found in {folder}")

    if index is not None:
        if index < 0 or index >= len(files):
            raise IndexError(f"Index {index} is out of range (0..{len(files)-1})")
        return str(files[index])

    # Default: first video
    return str(files[0])

def run_vlc(vlc_path: str, targets: list[str], fullscreen: bool, loop: bool, exit_when_done: bool):
    args = [vlc_path]
    if fullscreen:
        args.append("--fullscreen")
    args.append("--no-video-title-show")
    if loop:
        args.append("--loop")
    if exit_when_done:
        args.append("--play-and-exit")
    args += targets
    # Launch VLC (non-blocking)
    subprocess.Popen(args, shell=False)

def main():
    ap = argparse.ArgumentParser(description="Find VLC and play a video from a folder.")
    ap.add_argument("folder", help="Folder path containing your video(s)")
    ap.add_argument("--file", help="Specific filename inside the folder to play (optional)")
    ap.add_argument("--index", type=int, help="Play Nth video in folder (0-based) if --file not used")
    ap.add_argument("--all", action="store_true", help="Play the whole folder as a playlist")
    ap.add_argument("--loop", action="store_true", help="Loop playback (useful with --all)")
    ap.add_argument("--no-fullscreen", action="store_true", help="Do not start in fullscreen")
    ap.add_argument("--dry-run", action="store_true", help="Print what would run, without launching VLC")
    args = ap.parse_args()

    vlc = find_vlc()
    if not vlc:
        print("❌ Could not find VLC. Install VLC or set VLC_PATH env var to vlc.exe")
        sys.exit(1)

    folder = Path(args.folder)
    if args.all:
        targets = [str(folder.resolve())]  # VLC will load the directory as a playlist
        chosen = "(entire folder)"
        exit_when_done = False if args.loop else True
    else:
        # pick a single file
        chosen_file = pick_video(folder, args.file, args.index)
        targets = [chosen_file]
        exit_when_done = True

    print(f"VLC: {vlc}")
    print(f"Target: {targets[0]}")
    print(f"Options: fullscreen={not args.no_fullscreen}, loop={args.loop}, play_and_exit={exit_when_done}")

    if not args.dry_run:
        run_vlc(
            vlc_path=vlc,
            targets=targets,
            fullscreen=not args.no_fullscreen,
            loop=args.loop,
            exit_when_done=exit_when_done
        )

if __name__ == "__main__":
    main()

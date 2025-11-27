# pip install upnpclient lxml
import upnpclient
from urllib.parse import urljoin

TV_IP = "192.168.0.135"              # your TV
MEDIA_URL = "http://192.168.0.100:8000/Kicktracks.mp4"  # must be reachable by the TV over HTTP
                                         # (no file://, and not your localhost unless the TV can reach it)

def pick_renderer(devices):
    # Choose the LG MediaRenderer; prefer the exact IP or the device_type
    for d in devices:
        if d.device_type.endswith("MediaRenderer:1") and d.location.startswith(f"http://{TV_IP}"):
            return d
    # fallback: any MediaRenderer
    for d in devices:
        if d.device_type.endswith("MediaRenderer:1"):
            return d
    return None

def main():
    devs = upnpclient.discover()
    if not devs:
        raise SystemExit("No UPnP devices found")

    d = pick_renderer(devs)
    if not d:
        raise SystemExit("No MediaRenderer found (LG TV not visible)")

    # Grab the services
    avt = next(s for s in d.services if s.service_type.endswith("AVTransport:1"))
    rc  = next(s for s in d.services if s.service_type.endswith("RenderingControl:1"))
    cm  = next(s for s in d.services if s.service_type.endswith("ConnectionManager:1"))

    # Optional: inspect supported sink protocol infos
    sink = cm.GetProtocolInfo()["Sink"]  # e.g. 'http-get:*:video/mp4:*;http-get:*:image/jpeg:*;...'
    print("Supported SINK protocols:", sink)

    # Minimal DIDL-Lite metadata (many LGs accept empty metadata too)
    # If you get format errors, try leaving CurrentURIMetaData="" entirely.
    didl = f"""<?xml version="1.0" encoding="utf-8"?>
<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
           xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="0" parentID="0" restricted="1">
    <dc:title>Ad Video</dc:title>
    <upnp:class>object.item.videoItem</upnp:class>
    <res protocolInfo="http-get:*:video/mp4:*">{MEDIA_URL}</res>
  </item>
</DIDL-Lite>"""

    # 1) Tell the TV what to play
    # InstanceID is almost always 0 for single-zone renderers
    avt.SetAVTransportURI(
        InstanceID=0,
        CurrentURI=MEDIA_URL,
        CurrentURIMetaData=didl  # try "" if TV complains
    )

    # 2) Start playback
    avt.Play(InstanceID=0, Speed="1")

    # 3) Optional: set volume to 15
    rc.SetVolume(InstanceID=0, Channel="Master", DesiredVolume=15)

    # 4) Read back state
    info = avt.GetTransportInfo(InstanceID=0)
    pos  = avt.GetPositionInfo(InstanceID=0)
    print("State:", info)         # e.g. {'CurrentTransportState': 'PLAYING', ...}
    print("Position:", pos)       # e.g. {'RelTime': '0:00:03', 'TrackDuration': '0:01:00', ...}

if __name__ == "__main__":
    main()

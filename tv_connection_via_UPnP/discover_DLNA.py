import upnpclient
devs = upnpclient.discover()
for d in devs:
    print("DEVICE:", d.friendly_name, d.device_type, d.location)
    print("  services:", [s.service_type.split(":")[-1] for s in d.services])

import json, ssl, time, os
import websocket

TV_IP = "192.168.0.135"
PORTS = [3000, 3001]  # try 3000 then 3001
CLIENT_KEY_FILE = "webos_client_key.json"

manifest = {
    "manifestVersion": 1,
    "appVersion": "1.1",
    "signed": {
        "created": "2024-01-01T00:00:00Z",
        "appId": "com.example.pycontroller",
        "vendorId": "com.example",
        "localizedAppNames": {"": "Python Controller"},
        "localizedVendorNames": {"": "Example Inc"},
        "permissions": [
            "LAUNCH",
            "LAUNCH_WEBAPP",
            "APP_TO_APP",
            "CONTROL_AUDIO",
            "CONTROL_DISPLAY",
            "CONTROL_INPUT_MEDIA_PLAYBACK",
            "CONTROL_POWER",
            "READ_INSTALLED_APPS",
            "READ_LGE_SDX",
            "READ_INPUT_DEVICE_LIST",
            "READ_NETWORK_STATE",
            "READ_CURRENT_CHANNEL",
            "READ_RUNNING_APPS",
            "READ_TV_CHANNEL_LIST",
        ],
        "serial": "000000"
    },
    "permissions": [
        "LAUNCH",
        "LAUNCH_WEBAPP",
        "APP_TO_APP",
        "CONTROL_AUDIO",
        "CONTROL_DISPLAY",
        "CONTROL_INPUT_MEDIA_PLAYBACK",
        "CONTROL_POWER",
        "READ_INSTALLED_APPS",
        "READ_NETWORK_STATE",
        "READ_RUNNING_APPS"
    ]
}

def load_client_key():
    if os.path.exists(CLIENT_KEY_FILE):
        with open(CLIENT_KEY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("client-key")
    return None

def save_client_key(key):
    with open(CLIENT_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump({"client-key": key}, f)
        print(f"Saved client-key to {CLIENT_KEY_FILE}")

def try_connect(port):
    print(f"Connecting to ws://{TV_IP}:{port} (subprotocol lgtv2)...")
    ws = websocket.create_connection(
        f"ws://{TV_IP}:{port}",
        subprotocols=["lgtv2"],          # ← IMPORTANT!
        sslopt={"cert_reqs": ssl.CERT_NONE},
        timeout=5
    )
    return ws

def main():
    last_err = None
    for port in PORTS:
        try:
            ws = try_connect(port)
            print("Connected. Sending register…")
            client_key = load_client_key()

            payload = {
                "type": "register",
                "id": "register_0",
                "payload": {
                    "forcePairing": False,
                    "pairingType": "PROMPT",
                    "manifest": manifest
                }
            }
            # if we already paired once, include the key to skip prompt
            if client_key:
                payload["payload"]["client-key"] = client_key

            ws.send(json.dumps(payload))
            # TV should either pop up a pairing dialog or accept immediately
            for _ in range(5):
                msg = ws.recv()
                print("TV:", msg)
                data = json.loads(msg)
                # when pairing accepted, TV returns client-key
                if data.get("type") == "registered" and "client-key" in data.get("payload", {}):
                    ck = data["payload"]["client-key"]
                    print("✅ Paired! client-key =", ck)
                    save_client_key(ck)
                    ws.close()
                    return
                time.sleep(0.2)

            ws.close()
            return
        except Exception as e:
            last_err = e
            print(f"Failed on port {port}: {e}")
            time.sleep(0.5)

    print("❌ Could not establish a proper webOS session.", last_err)

if __name__ == "__main__":
    main()

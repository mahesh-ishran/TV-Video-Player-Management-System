import websocket
import ssl

TV_IP = "192.168.0.135"     # your TV’s IP
PORT   = 3000               # or 3001 if 3000 fails

try:
    print(f"Connecting to ws://{TV_IP}:{PORT} ...")
    ws = websocket.create_connection(
        f"ws://{TV_IP}:{PORT}",
        sslopt={"cert_reqs": ssl.CERT_NONE},
        timeout=5
    )
    print("✅ Connected successfully!")

    # Send a dummy hello (the TV might ignore it, that's OK)
    ws.send("hello")
    try:
        print("TV replied:", ws.recv())
    except Exception:
        print("No readable reply (expected for this test).")
    ws.close()
except Exception as e:
    print("❌ Connection failed:", e)

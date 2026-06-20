import socket
import requests
import time
from os import getenv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get these values from your .env file
HA_IP = getenv("HA_IP", "127.0.0.1")  # Home Assistant IP
HA_TOKEN = getenv("HA_TOKEN", "")  # Home Assistant Long-Lived Access Token
RA_IP = "127.0.0.1"  # RetroArch IP
RA_PORT = 55355  # Default RetroArch Network Port
CHECK_INTERVAL = 5  # Seconds between checks

HA_URL = f"http://{HA_IP}:8123/api/states/sensor.retroarch_status"
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

ICON_KEYWORDS = [
    ("gamecube", "mdi:nintendo-wii"),
    ("wii", "mdi:nintendo-wii"),
    ("snes", "mdi:nintendo-snes"),
    ("super nintendo", "mdi:nintendo-snes"),
    ("nes", "mdi:nintendo-nes"),
    ("famicom", "mdi:nintendo-nes"),
    ("genesis", "mdi:sega-genesis"),
    ("mega drive", "mdi:sega-genesis"),
    ("playstation", "mdi:sony-playstation"),
    ("psx", "mdi:sony-playstation"),
    ("psp", "mdi:sony-playstation"),
    ("nintendo 64", "mdi:nintendo-64"),
    ("n64", "mdi:nintendo-64"),
    ("game boy", "mdi:nintendo-gameboy"),
    ("gameboy", "mdi:nintendo-gameboy"),
    ("gba", "mdi:nintendo-gameboy"),
    ("dreamcast", "mdi:sega-dreamcast"),
    ("mame", "mdi:arcade"),
    ("arcade", "mdi:arcade"),
]


def get_retroarch_status():
    """Queries RetroArch via UDP for current status."""
    sock = None
    try:
        # RetroArch uses UDP for network commands
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        # Send the GET_STATUS command
        sock.sendto(b"GET_STATUS", (RA_IP, RA_PORT))
        data, _ = sock.recvfrom(1024)
        return data.decode("utf-8")
    except (socket.timeout, ConnectionRefusedError):
        return "DISCONNECTED"
    except Exception as e:
        print(f"Error communicating with RetroArch: {e}")
        return "ERROR"
    finally:
        if sock:
            sock.close()


def get_icon_for_game_type(game_type):
    """Map game type text to a Home Assistant icon."""
    game_type_lower = game_type.lower()
    for keyword, icon in ICON_KEYWORDS:
        if keyword in game_type_lower:
            return icon
    return "mdi:controller"


def parse_retroarch_status(raw_status):
    """Parse RetroArch GET_STATUS response into sensor fields."""
    parsed = {
        "state": "Idle",
        "icon": "mdi:controller-off",
        "game_type": "Unknown",
        "game_name": "Unknown",
    }

    status_text = raw_status.strip()
    if status_text == "DISCONNECTED":
        return parsed

    if status_text == "ERROR":
        parsed["state"] = "Error"
        parsed["icon"] = "mdi:alert-circle"
        return parsed

    if not status_text.startswith("GET_STATUS "):
        return parsed

    payload = status_text[len("GET_STATUS "):]
    if payload == "CONTENTLESS":
        parsed["state"] = "Stopped"
        parsed["icon"] = "mdi:stop-circle"
        return parsed

    if payload.startswith("PAUSED "):
        parsed["state"] = "Paused"
        details = payload[len("PAUSED "):]
    elif payload.startswith("PLAYING "):
        parsed["state"] = "Playing"
        details = payload[len("PLAYING "):]
    else:
        return parsed

    parts = details.split(",")
    system_id = parts[0].strip()
    game_name = parts[1].strip() if len(parts) > 1 else ""

    if system_id and system_id.upper() != "UNKNOWN":
        parsed["game_type"] = system_id
        parsed["icon"] = get_icon_for_game_type(system_id)
    else:
        parsed["icon"] = "mdi:controller"

    if game_name:
        parsed["game_name"] = game_name

    return parsed


def update_home_assistant(state, attributes):
    """Sends a POST request to Home Assistant to update the sensor."""
    payload = {
        "state": state,
        "attributes": attributes,
    }
    # Update Home Assistant with the new state and attributes
    print(f"Updating Home Assistant: {state} - {attributes['game_name']} ({attributes['game_type']})")
    try:
        response = requests.post(HA_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error updating Home Assistant: {e}")


def main():
    print(f"Monitoring RetroArch on {RA_IP}:{RA_PORT}...")
    while True:
        raw_status = get_retroarch_status()
        parsed = parse_retroarch_status(raw_status)

        # Create attributes dictionary for Home Assistant
        attributes = {
            "friendly_name": "RetroArch Status",
            "icon": parsed["icon"],
            "game_type": parsed["game_type"],
            "game_name": parsed["game_name"],
            "raw_response": raw_status,
        }

        update_home_assistant(parsed["state"], attributes)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

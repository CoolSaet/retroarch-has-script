import socket
import requests
import time
import json
from os import getenv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get these values from your .env file 
HA_IP = getenv("HA_IP", "127.0.0.1")  # Home Assistant IP
HA_TOKEN = getenv("HA_TOKEN", "")  # Home Assistant Long-Lived Access Token
RA_IP = "127.0.0.1" # RetroArch IP
RA_PORT = 55355   # Default RetroArch Network Port
CHECK_INTERVAL = 5  # Seconds between checks

HA_URL = f"http://{HA_IP}:8123/api/states/sensor.retroarch_status"
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def get_retroarch_status():
    """Queries RetroArch via UDP for current status."""
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
        sock.close()

def update_home_assistant(state, attributes):
    """Sends a POST request to Home Assistant to update the sensor."""
    payload = {
        "state": state,
        "attributes": attributes
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
               
        # Determine state and icon based on RetroArch response
        # RetroArch returns "GET_STATUS PLAYING [core_name],[game_name]"
        game_name = "Unknown"
        game_type = "Unknown"

        # Status
        if "PLAYING" in raw_status:
            state = "Playing"
        elif "PAUSED" in raw_status:
            state = "Paused"
        elif "CONTENTLESS" in raw_status:
            state = "Stopped"
            icon = "mdi:stop-circle"
        else:
            state = "Idle"
            icon = "mdi:controller-off"

        # Game Type
        if "gamecube" in raw_status.lower():
            icon = "mdi:nintendo-wii"
            game_type = "GameCube/Wii"
        elif "snes" in raw_status.lower():
            icon = "mdi:nintendo-snes"
            game_type = "SNES"
        elif "nes" in raw_status.lower():
            icon = "mdi:nintendo-nes"
            game_type = "NES"
        elif "genesis" in raw_status.lower() or "megadrive" in raw_status.lower():
            icon = "mdi:sega-genesis"
            game_type = "Genesis/Mega Drive"
        elif "ps1" in raw_status.lower() or "playstation" in raw_status.lower():
            icon = "mdi:sony-playstation"
            game_type = "PlayStation 1"
        elif "ps2" in raw_status.lower():
            icon = "mdi:sony-playstation"
            game_type = "PlayStation 2"
        elif "n64" in raw_status.lower() or "nintendo 64" in raw_status.lower():
            icon = "mdi:nintendo-64"
            game_type = "Nintendo 64"
        elif "gba" in raw_status.lower():
            icon = "mdi:nintendo-gameboy"
            game_type = "Game Boy Advance"
        elif "gb" in raw_status.lower() and "gba" not in raw_status.lower():
            icon = "mdi:nintendo-gameboy"
            game_type = "Game Boy"
        elif "psp" in raw_status.lower():
            icon = "mdi:sony-playstation"
            game_type = "PlayStation Portable"
        elif "dreamcast" in raw_status.lower():
            icon = "mdi:sega-dreamcast"
            game_type = "Dreamcast"
        elif "mame" in raw_status.lower():
            icon = "mdi:arcade"
            game_type = "MAME Arcade"
        else:
            game_type = "Unknown"

        # Game Name Extraction
        game_name = "Unknown"
        if "PLAYING" in raw_status:
            try:
                parts = raw_status.split("PLAYING")[1].strip().split(",")
                if len(parts) >= 2:
                    game_name = parts[1].strip()
                elif len(parts) == 1:
                    game_name = parts[0].strip()
            except Exception as e:
                print(f"Error parsing game name: {e}")

        # Create attributes dictionary for Home Assistant
        attributes = {
            "friendly_name": "RetroArch Status",
            "icon": icon,
            "game_type": game_type,
            "game_name": game_name,
            "raw_response": raw_status
        }

        update_home_assistant(state, attributes)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

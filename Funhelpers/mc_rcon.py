import socket
import struct
import re
from flask import current_app

def strip_mc_codes(text):
    """
    Strips Minecraft color/formatting codes (§ or & followed by a char)
    and also removes square brackets from ranks.
    """
    if not text:
        return ""
    # Remove § and & codes
    clean = re.sub(r'[§&][0-9a-fk-or]', '', text)
    # Remove [ and ]
    clean = clean.replace('[', '').replace(']', '')
    return clean.strip()

def run_rcon_command(command):
    """
    Runs an RCON command using a custom socket-based client.
    Avoids signal issues found in some libraries.
    """
    host = current_app.config.get("RCON_HOST", "35.210.3.240")
    # Strip brackets if present (common for IPv6 in URLs/configs)
    host = host.strip("[]")
    port = current_app.config.get("RCON_PORT", 25575)
    password = current_app.config.get("RCON_PASSWORD")
    
    if not password:
        return "Error: RCON password not configured"
        
    try:
        # Create connection (handles both IPv4 and IPv6 automatically)
        sock = socket.create_connection((host, port), timeout=5)
        
        def send_packet(packet_type, payload):
            # Packet structure: Length (4) | Request ID (4) | Type (4) | Payload (N) | 2 null bytes (2)
            packet_id = 0
            packet = struct.pack("<iii", len(payload) + 10, packet_id, packet_type) + payload.encode('utf-8') + b"\x00\x00"
            sock.sendall(packet)
            
            # Read response
            resp_len = struct.unpack("<i", sock.recv(4))[0]
            resp_data = sock.recv(resp_len)
            resp_id, resp_type = struct.unpack("<ii", resp_data[:8])
            resp_payload = resp_data[8:-2].decode('utf-8')
            return resp_id, resp_type, resp_payload

        # 1. Login (Type 3)
        resp_id, resp_type, _ = send_packet(3, password)
        if resp_id == -1:
            return "Error: RCON Authentication failed"
            
        # 2. Execute Command (Type 2)
        _, _, response = send_packet(2, command)
        
        sock.close()
        print(f"DEBUG RCON: Response: {response.strip()}", flush=True)
        return response.strip()
        
    except Exception as e:
        print(f"DEBUG RCON: Error: {str(e)}", flush=True)
        return f"Error: {str(e)}"

def get_player_stats(player_name):
    """
    Fetches stats for a player using PlaceholderAPI via RCON.
    Note: Player must be online for PAPI to retrieve values.
    """
    if not player_name:
        return {}
        
    # 1. Check if player is actually online using 'list' command
    online_res = run_rcon_command("list")
    is_online = False
    if online_res and "Error" not in online_res:
        # Strip color codes from the list response
        clean_list = strip_mc_codes(online_res)
        
        # 'list' usually returns: "There are 1 of 20 players online: player1, player2"
        # Or: "Admins: ADMIN mjsousa"
        if ":" in clean_list:
            # We look at the entire part after the first colon to be safe with multiline responses
            players_part = clean_list.split(":", 1)[1].lower()
            is_online = player_name.lower() in players_part
        else:
            is_online = player_name.lower() in clean_list.lower()

    placeholders = {
        "uuid": "%player_uuid%",
        "rank": "%luckperms_prefix%",
        "bank": "%vault_eco_balance%",
        "rem_claims": "%griefprevention_remainingclaims%",
        "total_claims": "%griefprevention_claims%",
        "last_online": "%essentials_last_login_date%"
    }
    
    raw_stats = {}
    for key, placeholder in placeholders.items():
        cmd = f"papi parse {player_name} {placeholder}"
        res = run_rcon_command(cmd)
        print(f"DEBUG RCON: PAPI {placeholder} -> '{res}'", flush=True)
        if res and "Error" not in res and res.strip() != placeholder:
            raw_stats[key] = res.strip()
        else:
            raw_stats[key] = "NA"
            
    # 3. Fallback: If UUID or last_online is NA, try to get it from 'seen' command
    if raw_stats["uuid"] == "NA" or raw_stats["last_online"] == "NA":
        seen_res_raw = run_rcon_command(f"seen {player_name}")
        if seen_res_raw and "Error" not in seen_res_raw:
            seen_res = strip_mc_codes(seen_res_raw)
            import re
            # Extract UUID
            if raw_stats["uuid"] == "NA":
                match_uuid = re.search(r"UUID:\s*([a-f0-9\-]+)", seen_res)
                if match_uuid:
                    raw_stats["uuid"] = match_uuid.group(1)
            
            # Extract "offline since X"
            if raw_stats["last_online"] == "NA":
                # Look for "offline since 6 seconds" or similar
                match_seen = re.search(r"offline since (.*)", seen_res, re.IGNORECASE)
                if match_seen:
                    raw_stats["last_online"] = f"{match_seen.group(1).split('.')[0].strip()} ago"
                elif "online since" in seen_res.lower():
                    raw_stats["last_online"] = "Now"

    # Format claims
    stats = {
        "uuid": raw_stats["uuid"],
        "rank": strip_mc_codes(raw_stats["rank"]),
        "bank": raw_stats["bank"],
        "claims": f"{raw_stats['rem_claims']}/{raw_stats['total_claims']}" if raw_stats['rem_claims'] != "NA" else "NA",
        "last_online": raw_stats["last_online"],
        "is_online": is_online
    }
            
    return stats

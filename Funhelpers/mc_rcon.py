import socket
import struct
from flask import current_app

def run_rcon_command(command):
    """
    Runs an RCON command using a custom socket-based client.
    Avoids signal issues found in some libraries.
    """
    host = current_app.config.get("RCON_HOST", "35.210.3.240")
    port = current_app.config.get("RCON_PORT", 25575)
    password = current_app.config.get("RCON_PASSWORD")
    
    if not password:
        return "Error: RCON password not configured"
        
    print(f"DEBUG RCON: Attempting connection to {host}:{port}", flush=True)
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
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
        
    placeholders = {
        "uuid": "%player_uuid%",
        "rank": "%luckperms_prefix%",
        "bank": "%vault_eco_balance%",
        "rem_claims": "%griefprevention_remainingclaims%",
        "total_claims": "%griefprevention_claims%"
    }
    
    raw_stats = {}
    for key, placeholder in placeholders.items():
        cmd = f"papi parse {player_name} {placeholder}"
        res = run_rcon_command(cmd)
        if res and "Error" not in res and res.strip() != placeholder:
            raw_stats[key] = res.strip()
        else:
            raw_stats[key] = "NA"
            
    # Format claims
    stats = {
        "uuid": raw_stats["uuid"],
        "rank": raw_stats["rank"],
        "bank": raw_stats["bank"],
        "claims": f"{raw_stats['rem_claims']}/{raw_stats['total_claims']}" if raw_stats['rem_claims'] != "NA" else "NA"
    }
            
    return stats

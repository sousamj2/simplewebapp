from mcstatus import JavaServer
import socket

def get_mc_status():
    """
    Queries the Minecraft server at mc.mjcrafts.pt using standard SLP (Server List Ping).
    Returns a dictionary with status information.
    """
    server_address = "mc.mjcrafts.pt"
    status_dict = {
        "online": False,
        "players_online": 0,
        "players_max": 0,
        "motd": "",
        "latency": 0
    }
    
    try:
        # We ping the server with a very short timeout
        server = JavaServer.lookup(server_address, timeout=1.5)
        status = server.status()
        
        status_dict["online"] = True
        status_dict["players_online"] = status.players.online
        status_dict["players_max"] = status.players.max
        status_dict["motd"] = status.description
        status_dict["latency"] = round(status.latency, 2)
        
    except (socket.timeout, ConnectionRefusedError, Exception) as e:
        # If any error occurs, we assume the server is offline
        # print(f"Error querying Minecraft server: {e}")
        pass
        
    return status_dict

from urllib.parse import quote_plus
from markupsafe import Markup

from .format_data import format_data
from flask import session
from .mc_rcon import get_player_stats


def render_profile_template(template_text):

    userinfo = session.get("userinfo", {})
    metadata = session.get("metadata", {})
    # print("lastlogints",metadata.get("lastlogints", ""))
    template_text = str(template_text)
    
    # Core user info
    rendered = template_text.replace("{{user_picture}}", userinfo.get("picture", ""))
    rendered = rendered.replace("{{nome}}", " ".join([metadata.get("first_name", ""), metadata.get("last_name", "")]))
    rendered = rendered.replace("{{email}}", metadata.get("email", ""))
    rendered = rendered.replace("{{lastlogin}}", format_data(metadata.get("lastlogints", "")))
    rendered = rendered.replace("{{ign}}", str(metadata.get("ign", "NA")))
    
    # Minecraft Stats (Fetch if server is likely online)
    ign = metadata.get("ign")
    print("DEBUG", ign, flush=True)
    if ign:
        stats = get_player_stats(ign)
        print("DEBUG", stats, flush=True)
        rendered = rendered.replace("{{player_rank}}", stats.get("rank", "NA"))
        rendered = rendered.replace("{{player_bank}}", stats.get("bank", "NA"))
        rendered = rendered.replace("{{player_claims}}", stats.get("claims", "NA"))
        rendered = rendered.replace("{{player_uuid}}", stats.get("uuid", "NA"))
    else:
        rendered = rendered.replace("{{player_rank}}", "NA")
        rendered = rendered.replace("{{player_bank}}", "NA")
        rendered = rendered.replace("{{player_claims}}", "NA")
        rendered = rendered.replace("{{player_uuid}}", "NA")

    rendered = rendered.replace("{{error_message}}", str(metadata.get("error_message", "")))

    return Markup(rendered)



def format_address_for_url(address):
    """
    Takes an address string and returns it formatted for use in a URL.
    
    Args:
        address (str): The address to format (e.g., "Rua Cidade de Nampula, 1, 1800 Lisboa")
    
    Returns:
        str: URL-encoded address
    """
    return quote_plus(address)


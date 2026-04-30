from urllib.parse import quote_plus
from markupsafe import Markup

from .format_data import format_data
from flask import session


def render_profile_template(template_text):

    userinfo = session.get("userinfo", {})
    metadata = session.get("metadata", {})
    # print("lastlogints",metadata.get("lastlogints", ""))
    template_text = str(template_text)
    # Example replacements; add more as needed
    rendered = template_text.replace("{{user_picture}}", userinfo.get("picture", ""))
    rendered = rendered.replace("{{greeting}}", metadata.get("greeting", ""))
    rendered = rendered.replace("{{nome}}", " ".join([metadata.get("first_name", ""), metadata.get("last_name", "")]))
    rendered = rendered.replace("{{email}}", metadata.get("email", ""))
    rendered = rendered.replace("{{lastlogin}}", format_data(metadata.get("lastlogints", "")))
    rendered = rendered.replace("{{morada}}", metadata.get("full_address", ""))
    rendered = rendered.replace("{{codigopostal}}", str(metadata.get("zip_code1", ""))+'-'+str(metadata.get("zip_code2", ""))) 
    rendered = rendered.replace("{{nif}}", str(metadata.get("nfiscal", "")))
    rendered = rendered.replace("{{telemovel}}", str(metadata.get("cell_phone", "")))

    rendered = rendered.replace("{{cell_phone}}", str(metadata.get("cell_phone", "")))
    rendered = rendered.replace("{{zip_code1}}", str(metadata.get("zip_code1", "")))
    rendered = rendered.replace("{{zip_code2}}", str(metadata.get("zip_code2", "")))
    rendered = rendered.replace("{{address}}", str(metadata.get("address", "")))
    rendered = rendered.replace("{{number}}", str(metadata.get("number", "")))
    rendered = rendered.replace("{{floor}}", str(metadata.get("floor", "")))
    rendered = rendered.replace("{{door}}", str(metadata.get("door", "")))
    rendered = rendered.replace("{{nfiscal}}", str(metadata.get("nfiscal", "")))
    rendered = rendered.replace("{{error_message}}", str(metadata.get("error_message", "")))
    rendered = rendered.replace("{{gg_address}}", str(format_address_for_url(metadata.get("g_address",""))))
    # Replace boolean fields for LEDs (example: 'green' if True else 'orange')
    vpn_check = metadata.get("vpn_check", False)
    primeiro_contacto = metadata.get("first_contact_complete", False)
    primeira_aula = metadata.get("first_session_complete", False)
    rendered = rendered.replace("{{vpn_check_color}}", "green" if vpn_check else "orange")
    rendered = rendered.replace("{{primeiro_contacto_color}}", "green" if primeiro_contacto else "orange")
    rendered = rendered.replace("{{primeira_aula_color}}", "green" if primeira_aula else "orange")

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


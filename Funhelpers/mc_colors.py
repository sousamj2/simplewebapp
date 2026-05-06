import re
from markupsafe import escape, Markup

MC_COLORS = {
    '0': '#000000',
    '1': '#0000AA',
    '2': '#00AA00',
    '3': '#00AAAA',
    '4': '#AA0000',
    '5': '#AA00AA',
    '6': '#FFAA00',
    '7': '#AAAAAA',
    '8': '#555555',
    '9': '#5555FF',
    'a': '#55FF55',
    'b': '#55FFFF',
    'c': '#FF5555',
    'd': '#FF55FF',
    'e': '#FFFF55',
    'f': '#FFFFFF',
}

MC_FORMATS = {
    'l': 'font-weight: bold;',
    'm': 'text-decoration: line-through;',
    'n': 'text-decoration: underline;',
    'o': 'font-style: italic;',
    'k': 'mc-magic', # Special class for animation
}

def mc_to_html(text):
    """
    Converts Minecraft color codes (§0-§f, §l-§o, §r) to HTML.
    Also handles newlines.
    """
    if not text:
        return ""
    
    # Handle potential JSON/Object MOTD if mcstatus returns it
    if not isinstance(text, str):
        text = str(text)

    # Escape HTML first
    text = str(escape(text))
    
    # Replace \n with <br>
    text = text.replace('\\n', '<br>').replace('\n', '<br>')
    
    # Split by the section symbol
    parts = re.split(r'§|\u00a7', text)
    
    result = []
    
    # First part has no color
    result.append(parts[0])
    
    open_spans = 0
    
    for part in parts[1:]:
        if not part:
            continue
        
        code = part[0].lower()
        content = part[1:]
        
        if code == 'r':
            # Reset: close all open spans
            while open_spans > 0:
                result.append('</span>')
                open_spans -= 1
            result.append(content)
        elif code in MC_COLORS:
            # Color: close current color if exists (simplified) 
            # and open new one
            # To be strictly correct we should reset or manage a stack
            # but usually colors override each other
            while open_spans > 0:
                result.append('</span>')
                open_spans -= 1
            result.append(f'<span style="color: {MC_COLORS[code]}">')
            result.append(content)
            open_spans += 1
        elif code in MC_FORMATS:
            style_or_class = MC_FORMATS[code]
            if code == 'k':
                result.append(f'<span class="{style_or_class}">')
            else:
                result.append(f'<span style="{style_or_class}">')
            result.append(content)
            open_spans += 1
        else:
            # Unknown code, just append it
            result.append(part)
            
    # Close any remaining spans
    while open_spans > 0:
        result.append('</span>')
        open_spans -= 1
        
    return Markup("".join(result))

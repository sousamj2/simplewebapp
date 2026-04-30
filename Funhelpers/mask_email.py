
def mask_email(email):
    # Mask email username partially e.g. ma***@email.com
    parts = email.split('@')
    if len(parts[0]) <= 2:
        return "***@" + parts[1]
    return parts[0][:2] + "*****@" + parts[1]

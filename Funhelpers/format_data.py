from datetime import datetime

def format_data(value):
    """
    Formats a datetime object or ISO string to a human-readable format.
    'data' in Portuguese means 'date'.
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            # Try to parse standard ISO format
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass
        
        # Try to parse another common format if it's just a date string
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return str(value)

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
        
    return str(value)

"""Phone number validation utilities"""

import re
import phonenumbers
from phonenumbers import NumberParseException


def validate_indian_phone(phone_number: str) -> tuple[bool, str]:
    """
    Validate and format Indian phone number.
    
    Args:
        phone_number: Phone number string
        
    Returns:
        Tuple of (is_valid, formatted_number)
    """
    # Remove any spaces, dashes, or parentheses
    phone_number = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # Check if it starts with +91 or 91
    if phone_number.startswith('+91'):
        phone_number = phone_number[3:]
    elif phone_number.startswith('91') and len(phone_number) > 10:
        phone_number = phone_number[2:]
    
    # Indian mobile numbers are 10 digits starting with 6-9
    if not re.match(r'^[6-9]\d{9}$', phone_number):
        return False, ""
    
    # Format as +91XXXXXXXXXX
    formatted = f"+91{phone_number}"
    
    # Validate using phonenumbers library
    try:
        parsed = phonenumbers.parse(formatted, None)
        if phonenumbers.is_valid_number(parsed):
            return True, formatted
    except NumberParseException:
        pass
    
    return False, ""


def format_phone_display(phone_number: str) -> str:
    """
    Format phone number for display.
    
    Args:
        phone_number: Phone number (e.g., +919876543210)
        
    Returns:
        Formatted phone number (e.g., +91 98765 43210)
    """
    if phone_number.startswith('+91'):
        number = phone_number[3:]
        return f"+91 {number[:5]} {number[5:]}"
    return phone_number


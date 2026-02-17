"""Shared password validation and generation utilities."""
import re
import secrets
import string

# Password policy constants
PASSWORD_MIN_LENGTH = 15
PASSWORD_RULES = [
    (r'[A-Z]', 'at least 1 uppercase letter'),
    (r'[a-z]', 'at least 1 lowercase letter'),
    (r'[0-9]', 'at least 1 number'),
    (r'[^A-Za-z0-9]', 'at least 1 special character'),
]


def validate_password(password):
    """Validate a password against complexity rules.

    Returns a list of error messages. Empty list means the password is valid.
    """
    errors = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long "
            f"(currently {len(password)})."
        )

    for pattern, description in PASSWORD_RULES:
        if not re.search(pattern, password):
            errors.append(f"Password must contain {description}.")

    return errors


def generate_password(length=20):
    """Generate a random password that satisfies all complexity rules.

    Guarantees at least one character from each required category,
    fills the rest randomly, then shuffles.
    """
    if length < PASSWORD_MIN_LENGTH:
        length = PASSWORD_MIN_LENGTH

    special_chars = '!@#$%^&*()-_=+[]{}|;:,.<>?'

    # Guarantee one from each category
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(special_chars),
    ]

    # Fill remaining length from all categories
    all_chars = string.ascii_letters + string.digits + special_chars
    for _ in range(length - len(chars)):
        chars.append(secrets.choice(all_chars))

    # Shuffle to avoid predictable positions
    result = list(chars)
    secrets.SystemRandom().shuffle(result)
    return ''.join(result)

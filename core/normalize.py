"""Name normalization for configuration item matching."""
import re

# Words that carry no identity for an application name.
STOP_WORDS = {"the", "app", "application", "prod", "production", "inc", "llc", "corp"}


def normalize_name(name):
    """Lowercase, strip punctuation, and drop non-identifying words.

    "The Apex-Billing App" -> "apex billing"
    """
    s = re.sub(r"[^a-z0-9]+", " ", name.lower())
    return " ".join(t for t in s.split() if t not in STOP_WORDS)

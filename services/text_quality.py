import re
from typing import Optional


def is_gibberish_text(text: Optional[str]) -> bool:
    t = (text or "").strip()
    if len(t) < 4:
        return True
    low = t.lower()
    suspicious = ("weh weh", "do stoint", "sosday", "nstra", "divertuz")
    if any(token in low for token in suspicious):
        return True
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", t)
    if len(words) < 2:
        return True
    unique_ratio = len(set(w.lower() for w in words)) / max(1, len(words))
    if unique_ratio < 0.34:
        return True
    consonant_heavy = 0
    for w in words:
        lw = w.lower()
        if len(lw) >= 6 and not re.search(r"[aeiouyаеёиоуыэюя]", lw):
            consonant_heavy += 1
    if words and consonant_heavy / len(words) > 0.45:
        return True
    return False

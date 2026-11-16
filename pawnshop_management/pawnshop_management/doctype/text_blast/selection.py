"""Text Blast encoding and date matching rules (no database side effects)."""
import math
from datetime import datetime, timedelta

GSM_BASIC = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM_EXTENDED = set("\f^{}\\[~]|€")
FILTER_TYPES = (
    "Registered date range", "Subastado sales date range", "Agreement to sell date range",
    "Pawn ticket date range", "FX selling date range", "FX buying date range",
)


def sms_metrics(message):
    message = message or ""
    unsupported = list(dict.fromkeys(c for c in message if c not in GSM_BASIC | GSM_EXTENDED))
    unicode = bool(unsupported)
    units = len(message.encode("utf-16-be")) // 2 if unicode else sum(2 if c in GSM_EXTENDED else 1 for c in message)
    single, multipart = (70, 67) if unicode else (160, 153)
    segments = (1 if units <= single else math.ceil(units / multipart)) if units else 0
    return dict(characters=len(message), units=units, encoding="Unicode" if unicode else "GSM", segments=segments, unsupported=unsupported)


def registration_matches(tracker, start, end):
    suffix = str(tracker or "").rsplit("-", 1)[-1]
    if not suffix.isdigit():
        return False
    if len(suffix) == 8:
        try:
            return start <= datetime.strptime(suffix, "%m%d%Y").date() <= end
        except ValueError:
            return False
    if 4 <= len(suffix) < 8:
        return start.year <= int(suffix[-4:]) <= end.year
    return False


def sheet_transaction_date(value):
    if isinstance(value, (float, int)):
        return (datetime(1899, 12, 30) + timedelta(days=value)).date()
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.split(" ")[0].split("T")[0], fmt).date()
        except ValueError:
            pass
    return None


def fx_buying_trackers(rows, start, end):
    matches = set()
    for row in rows:
        if len(row) < 4 or (len(row) > 13 and str(row[13]).strip()):
            continue
        date = sheet_transaction_date(row[1])
        if date and start <= date <= end:
            tracker = str(row[3] or "").split("~", 1)[0].strip()
            if tracker:
                matches.add(tracker)
    return matches

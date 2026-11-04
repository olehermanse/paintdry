import json
import smtplib
from email.message import EmailMessage

from paintdry.lib import Change

# Lowest to highest, see Severity in README.md ("unknown" and "" are never
# alerts):
SEVERITIES = ["none", "notice", "recommendation", "low", "medium", "high", "critical"]
SECRETS_JSON = "config/secrets.json"
# Values can be huge (e.g. commit_signatures), the whole change is in the UI:
MAX_VALUE_LENGTH = 200


def is_alert(severity: str, min_severity: str) -> bool:
    if severity not in SEVERITIES or min_severity not in SEVERITIES:
        return False
    return SEVERITIES.index(severity) >= SEVERITIES.index(min_severity)


def get_smtp_secrets() -> dict | None:
    """The smtp object in secrets.json, or None if it's missing or invalid"""
    try:
        with open(SECRETS_JSON, "r") as f:
            return json.loads(f.read()).get("smtp")
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid {SECRETS_JSON}: {e}")
        return None


def shorten(value) -> str:
    value = value if isinstance(value, str) else json.dumps(value)
    if len(value) > MAX_VALUE_LENGTH:
        return value[:MAX_VALUE_LENGTH] + "..."
    return value


def send_alert_email(changes: list[Change], config: dict[str, str]):
    """Email the changes with alert_min_severity or above to alert_emails
    (config table). Errors are printed, not raised, so they don't stop the
    updater"""
    min_severity = config.get("alert_min_severity", "high")
    if min_severity not in SEVERITIES:
        # Don't silently stop alerting because of a typo:
        print(f"Warning: Invalid alert_min_severity '{min_severity}' - using 'high'")
        min_severity = "high"
    changes = [c for c in changes if is_alert(c.severity, min_severity)]
    recipients = [
        e.strip() for e in config.get("alert_emails", "").split(",") if e.strip()
    ]
    if not changes or not recipients:
        return
    smtp = get_smtp_secrets()
    if not smtp:
        print(f"Warning: No smtp in {SECRETS_JSON} - skipping {len(changes)} alert(s)")
        return

    lines = []
    for c in changes:
        lines.append(f"[{c.severity}] {c.resource} ({c.module}) {c.attribute}")
        lines.append(f"  Old value: {shorten(c.old_value)}")
        lines.append(f"  New value: {shorten(c.new_value)}")
        lines.append(f"  Change ID: {c.id}")
        lines.append("")
    try:
        message = EmailMessage()
        message["Subject"] = f"paintdry: {len(changes)} new alert(s)"
        message["From"] = smtp.get("from") or smtp["username"]
        message["To"] = ", ".join(recipients)
        message.set_content("\n".join(lines))
        port = smtp.get("port", 587)
        # 465 is TLS from the start, other ports (587) upgrade with STARTTLS:
        smtp_class = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with smtp_class(smtp["host"], port) as server:
            if port != 465:
                server.starttls()
            if "username" in smtp:
                server.login(smtp["username"], smtp["password"])
            server.send_message(message)
        print(f"Emailed {len(changes)} alert(s) to {message['To']}")
    except Exception as e:
        print(f"Error: Failed to email {len(changes)} alert(s): {e!r}")

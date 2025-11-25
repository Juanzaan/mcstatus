import requests
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def load_settings():
    """Load settings from settings.json"""
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except:
        return {"notifications": {"enabled": False}}

def send_discord_notification(webhook_url, title, description, color=0x3b82f6, fields=None):
    """Send a notification to Discord via webhook.
    
    Args:
        webhook_url: Discord webhook URL
        title: Embed title
        description: Embed description
        color: Embed color (hex)
        fields: List of field dicts with 'name' and 'value'
    """
    if not webhook_url:
        return False
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "MC Scanner Alerts"}
    }
    
    if fields:
        embed["fields"] = fields
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        return response.status_code == 204
    except Exception as e:
        print(f"[Discord] Failed to send notification: {e}")
        return False

def send_email_notification(smtp_config, subject, body):
    """Send an email notification.
    
    Args:
        smtp_config: Dict with smtp_server, smtp_port, from_email, to_email, password
        subject: Email subject
        body: Email body (HTML supported)
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_email']
        msg['To'] = smtp_config['to_email']
        
        # Add HTML body
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
            server.starttls()
            server.login(smtp_config['from_email'], smtp_config['password'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"[Email] Failed to send notification: {e}")
        return False

def check_and_notify_alerts(current_data, previous_data=None):
    """Check for alert conditions and send notifications.
    
    Args:
        current_data: List of current server data dicts
        previous_data: List of previous server data dicts (optional)
    
    Returns:
        Dict with alert counts
    """
    settings = load_settings()
    notifications_config = settings.get("notifications", {})
    alerts_config = settings.get("alerts", {})
    
    if not notifications_config.get("enabled"):
        return {"sent": 0, "skipped": "disabled"}
    
    alerts_sent = 0
    
    # Convert lists to dicts for easy lookup
    current_servers = {s['ip']: s for s in current_data}
    previous_servers = {s['ip']: s for s in previous_data} if previous_data else {}
    
    # Check for offline servers
    if alerts_config.get("server_offline", {}).get("enabled"):
        min_players = alerts_config["server_offline"].get("min_previous_online", 10)
        for ip, prev in previous_servers.items():
            if ip not in current_servers and prev.get('online', 0) >= min_players:
                notify_server_offline(notifications_config, ip, prev)
                alerts_sent += 1
    
    # Check for player spikes
    if alerts_config.get("player_spike", {}).get("enabled"):
        threshold = alerts_config["player_spike"].get("threshold_percent", 50)
        min_players = alerts_config["player_spike"].get("min_players", 100)
        for ip, current in current_servers.items():
            if ip in previous_servers:
                prev = previous_servers[ip]
                prev_count = prev.get('online', 0)
                curr_count = current.get('online', 0)
                if prev_count >= min_players and curr_count > 0:
                    percent_change = ((curr_count - prev_count) / prev_count) * 100
                    if abs(percent_change) >= threshold:
                        notify_player_spike(notifications_config, ip, current, percent_change)
                        alerts_sent += 1
    
    # Check for new premium servers
    if alerts_config.get("new_premium_server", {}).get("enabled"):
        min_players = alerts_config["new_premium_server"].get("min_players", 50)
        for ip, current in current_servers.items():
            if ip not in previous_servers:
                if current.get('auth_mode') == 'PREMIUM' and current.get('online', 0) >= min_players:
                    notify_new_premium_server(notifications_config, ip, current)
                    alerts_sent += 1
    
    return {"sent": alerts_sent}

def notify_server_offline(config, ip, server_data):
    """Send notification for server going offline."""
    title = "🔴 Server Offline"
    description = f"Server **{ip}** is now offline"
    fields = [
        {"name": "Previous Players", "value": str(server_data.get('online', 'N/A')), "inline": True},
        {"name": "Country", "value": server_data.get('country', 'Unknown'), "inline": True},
        {"name": "Auth Mode", "value": server_data.get('auth_mode', 'Unknown'), "inline": True}
    ]
    
    if config.get("discord", {}).get("enabled"):
        send_discord_notification(
            config["discord"]["webhook_url"],
            title, description, color=0xef4444, fields=fields
        )
    
    if config.get("email", {}).get("enabled"):
        body = f"<h2>{title}</h2><p>{description}</p>"
        send_email_notification(config["email"], title, body)

def notify_player_spike(config, ip, server_data, percent_change):
    """Send notification for player count spike."""
    direction = "📈" if percent_change > 0 else "📉"
    title = f"{direction} Player Spike Detected"
    description = f"Server **{ip}** has a **{abs(percent_change):.1f}%** change in players"
    fields = [
        {"name": "Current Players", "value": str(server_data.get('online', 'N/A')), "inline": True},
        {"name": "Change", "value": f"{percent_change:+.1f}%", "inline": True},
        {"name": "Country", "value": server_data.get('country', 'Unknown'), "inline": True}
    ]
    
    color = 0x10b981 if percent_change > 0 else 0xf59e0b
    
    if config.get("discord", {}).get("enabled"):
        send_discord_notification(
            config["discord"]["webhook_url"],
            title, description, color=color, fields=fields
        )
    
    if config.get("email", {}).get("enabled"):
        body = f"<h2>{title}</h2><p>{description}</p>"
        send_email_notification(config["email"], title, body)

def notify_new_premium_server(config, ip, server_data):
    """Send notification for new premium server discovered."""
    title = "✨ New Premium Server"
    description = f"Discovered new premium server: **{ip}**"
    fields = [
        {"name": "Players Online", "value": str(server_data.get('online', 'N/A')), "inline": True},
        {"name": "Country", "value": server_data.get('country', 'Unknown'), "inline": True},
        {"name": "Version", "value": server_data.get('version', 'Unknown'), "inline": True}
    ]
    
    if config.get("discord", {}).get("enabled"):
        send_discord_notification(
            config["discord"]["webhook_url"],
            title, description, color=0x10b981, fields=fields
        )
    
    if config.get("email", {}).get("enabled"):
        body = f"<h2>{title}</h2><p>{description}</p>"
        send_email_notification(config["email"], title, body)

if __name__ == "__main__":
    # Test notifications
    settings = load_settings()
    if settings.get("notifications", {}).get("discord", {}).get("enabled"):
        webhook = settings["notifications"]["discord"]["webhook_url"]
        send_discord_notification(
            webhook,
            "🧪 Test Notification",
            "This is a test message from the MC Scanner notification system.",
            fields=[{"name": "Status", "value": "Working!", "inline": True}]
        )
        print("Test Discord notification sent!")
    else:
        print("Discord notifications not enabled in settings.json")

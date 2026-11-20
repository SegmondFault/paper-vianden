#!/usr/bin/env python3
"""VulnCastle - Intentionally Vulnerable Webmail (Educational Purpose Only)"""
# nosemgrep
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

USERS = {
    "admin": "MailP@ss2024",
    "sysadmin": "admin123",
    "devuser": "devuser2024",
}

EMAILS = [
    {"from": "ceo@acme-corp.local", "to": "admin@acme-corp.local",
     "subject": "VPN Credentials", "body": "New VPN creds: vpnuser / Vpn$ecure99\nGateway: vpn-gw-01.internal"},
    {"from": "devops@acme-corp.local", "to": "sysadmin@acme-corp.local",
     "subject": "DB Migration", "body": "Production DB migrated.\nHost: db-01.internal\nUser: root\nPass: S3cretDB!2024"},
    {"from": "hr@acme-corp.local", "to": "admin@acme-corp.local",
     "subject": "New Employee Onboarding", "body": "Please create accounts for new hires.\nDefault password: Welcome2024!"},
]


class WebmailHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/login":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<html><head><title>ACME Webmail</title></head><body>
            <h1>ACME Corp Webmail</h1>
            <form method="POST" action="/login">
            <input name="user" placeholder="Username"><br>
            <input name="pass" type="password" placeholder="Password"><br>
            <button type="submit">Login</button>
            </form></body></html>""")
        elif parsed.path == "/inbox":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = "<html><head><title>Inbox</title></head><body><h1>Inbox</h1>"
            for i, email in enumerate(EMAILS):
                html += f"<div style='border:1px solid #ccc;padding:10px;margin:5px'>"
                html += f"<b>From:</b> {email['from']}<br>"
                html += f"<b>Subject:</b> {email['subject']}<br>"
                html += f"<pre>{email['body']}</pre></div>"
            html += "</body></html>"
            self.wfile.write(html.encode())
        elif parsed.path == "/debug":
            # Information disclosure: environment variables
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            env_dump = "\n".join(f"{k}={v}" for k, v in os.environ.items())
            self.wfile.write(env_dump.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)
        if self.path == "/login":
            user = params.get("user", [""])[0]
            pw = params.get("pass", [""])[0]
            # Vulnerable: no rate limiting, no account lockout
            if user in USERS and USERS[user] == pw:
                self.send_response(302)
                self.send_header("Location", "/inbox")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<html><body><p>Invalid credentials for user: {user}</p><a href='/'>Back</a></body></html>".encode())


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8025), WebmailHandler)
    print("Webmail running on port 8025")
    server.serve_forever()

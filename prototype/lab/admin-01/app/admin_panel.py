#!/usr/bin/env python3
"""VulnCastle - Intentionally Vulnerable Admin Panel (Educational Purpose Only)"""
# nosemgrep
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = "/opt/admin/admin.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT
    )""")
    c.execute("INSERT OR IGNORE INTO admins (id, username, password, role) VALUES (1, 'administrator', 'Admin!Panel99', 'superadmin')")
    c.execute("INSERT OR IGNORE INTO admins (id, username, password, role) VALUES (2, 'operator', 'operator123', 'operator')")
    conn.commit()
    conn.close()


class AdminHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/login":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<html><head><title>Admin Panel</title>
            <style>body{font-family:monospace;background:#1a1a2e;color:#e94560;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
            .panel{background:#16213e;padding:40px;border-radius:8px;border:1px solid #e94560}
            input{display:block;margin:10px 0;padding:8px;width:200px;background:#0f3460;border:1px solid #e94560;color:#fff}
            button{padding:10px 20px;background:#e94560;color:#fff;border:none;cursor:pointer;width:100%}</style></head>
            <body><div class="panel"><h1>ADMIN PANEL</h1>
            <form method="POST" action="/login">
            <input name="username" placeholder="Username">
            <input name="password" type="password" placeholder="Password">
            <button type="submit">ACCESS</button>
            </form></div></body></html>""")
        elif parsed.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            # No session validation (broken authentication)
            html = """<html><head><title>Dashboard</title></head><body style="background:#1a1a2e;color:#eee;font-family:monospace;padding:20px">
            <h1>System Dashboard</h1>
            <h2>Services</h2>
            <ul><li>Redis: admin-01:6379 (no auth)</li><li>DB: db-01:3306 (root/S3cretDB!2024)</li>
            <li>Samba: file-01:445</li><li>API: app-01:3000</li></ul>
            <h2>Server Info</h2><pre>"""
            html += f"Hostname: {os.uname().nodename}\n"
            html += f"User: {os.getenv('USER', 'root')}\n"
            html += f"PATH: {os.getenv('PATH')}\n"
            html += "</pre></body></html>"
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)
        if self.path == "/login":
            username = params.get("username", [""])[0]
            password = params.get("password", [""])[0]
            # SQL Injection vulnerability
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            query = f"SELECT * FROM admins WHERE username='{username}' AND password='{password}'"
            try:
                c.execute(query)
                result = c.fetchone()
                if result:
                    self.send_response(302)
                    self.send_header("Location", "/dashboard")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body style='background:#1a1a2e;color:#e94560;font-family:monospace;text-align:center;padding:50px'><h2>ACCESS DENIED</h2><a href='/' style='color:#e94560'>Back</a></body></html>")
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                # Error message leaks query details
                self.wfile.write(f"Database error: {e}\nQuery: {query}".encode())
            finally:
                conn.close()


if __name__ == "__main__":
    init_db()
    server = HTTPServer(("0.0.0.0", 8080), AdminHandler)
    print("Admin panel running on port 8080")
    server.serve_forever()

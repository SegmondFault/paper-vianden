#!/usr/bin/env python3
"""Inert banner emulators and non-forwarding DNS sink; no vulnerable software."""
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import socketserver
import struct
import threading
from fixture_dns import NAMES

DNS_LOG = logging.getLogger('dns-evidence')
LOG = logging.getLogger('scenario-sink')


def record(protocol, peer, **fields):
    LOG.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                         'simulated': True, 'protocol': protocol, 'source': peer,
                         **fields}))


def dns_reply(packet):
    if len(packet) < 17:
        raise ValueError('Short query')
    ident, flags, count, _, _, _ = struct.unpack('!6H', packet[:12])
    if flags & 0x8000 or count != 1:
        raise ValueError('Not a single query')
    offset, labels = 12, []
    while True:
        if offset >= len(packet):
            raise ValueError('Missing label')
        size = packet[offset]
        offset += 1
        if not size:
            break
        if size > 63 or offset+size > len(packet):
            raise ValueError('Invalid label')
        labels.append(packet[offset:offset+size].decode('ascii'))
        offset += size
    if offset+4 != len(packet) or offset > 267:
        raise ValueError('Invalid question')
    name = '.'.join(labels).lower()
    # NXDOMAIN for everything else; never forward queries anywhere.
    allowed = name.endswith('.telemetry.range.test') or name in NAMES
    answer = b''
    if name in NAMES and struct.unpack('!HH', packet[offset:offset+4]) == (1, 1):
        # Only Docker aliases from the fixed office allowlist; no recursion.
        ip = socket.inet_aton(socket.gethostbyname(NAMES[name]))
        answer = struct.pack('!HHHIH4s', 0xc00c, 1, 1, 60, 4, ip)
    header = struct.pack('!6H', ident, 0x8400 if allowed else 0x8403, 1, bool(answer), 0, 0)
    return name, header+packet[12:]+answer


class DNS(socketserver.BaseRequestHandler):
    def handle(self):
        packet, sock = self.request
        try:
            name, reply = dns_reply(packet)
            record('dns', self.client_address[0], query=name, bytes=len(packet))
            DNS_LOG.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                'protocol': 'dns', 'source': self.client_address[0], 'query': name,
                'bytes': len(packet), 'rcode': reply[3] & 15}))
            sock.sendto(reply, self.client_address)
        except (ValueError, UnicodeError, OSError):
            record('dns', self.client_address[0], result='rejected')


class SSH(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            self.request.sendall(b'SSH-2.0-OpenSSH_7.2p2 Ubuntu-4ubuntu2.10\r\n')
            banner = self.request.recv(128).decode('ascii', errors='replace')
            record('ssh', self.client_address[0], banner=banner)
        except OSError:
            pass


class Java(BaseHTTPRequestHandler):
    server_version = 'Apache-Coyote/1.1'
    sys_version = ''

    def do_GET(self):
        body = b'{"service":"portal","status":"ok"}\n'
        self.send_response(200)
        self.send_header('X-Powered-By', 'Servlet/3.0; JBossAS/6; Java/1.8.0_102')
        self.send_header('X-Range-Simulation', 'true')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        record('http', self.client_address[0], path=self.path[:256])

    def do_POST(self):
        # Inert, allowlisted markers only. Never execute request content.
        markers = {'/api/session': 'foothold-emulated',
                   '/api/profile': 'public-fixture-accounts-only',
                   '/api/status': 'synthetic-transfer-complete'}
        if self.path not in markers:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self.send_error(400)
            return
        if not 0 <= length <= 64 or self.headers.get('Transfer-Encoding'):
            self.send_error(400)
            return
        if self.rfile.read(length) != b'{}':
            self.send_error(400)
            return
        body = json.dumps({'ok': True}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        record('http-marker', self.client_address[0], marker=markers[self.path],
               code_execution=False)

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(2)


def main():
    LOG.setLevel(logging.INFO)
    LOG.addHandler(logging.StreamHandler())
    path = Path('/var/log/range-instructor/scenario-sink.jsonl')
    LOG.addHandler(RotatingFileHandler(path, maxBytes=524288, backupCount=1))
    DNS_LOG.setLevel(logging.INFO)
    DNS_LOG.addHandler(RotatingFileHandler('/var/log/dns/queries.jsonl', maxBytes=524288, backupCount=1))
    # Serial TCP/UDP handlers bound work; HTTP has bounded socket timeouts.
    servers = [socketserver.UDPServer(('0.0.0.0', 1053), DNS),
               socketserver.TCPServer(('0.0.0.0', 2222), SSH),
               ThreadingHTTPServer(('0.0.0.0', 8080), Java)]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    record('lifecycle', 'local', state='ready')
    threading.Event().wait()


if __name__ == '__main__':
    main()

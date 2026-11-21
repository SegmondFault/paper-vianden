"""Allowlisted office DNS fixtures; no recursion or external destinations."""
import os
import socket
import struct

HOSTS = {'portal': 'web-01.dmz', 'api': 'app-01.internal',
         'files': 'file-01.internal', 'directory': 'ldap.internal',
         'database': 'db-01.internal', 'gateway': 'vpn-gw-01.internal',
         'smtp': 'mail-sink.dmz', 'mail': 'mail.internal', 'ftp': 'ftp.dmz'}
NAMES = {name+'.office.range.test': host for name, host in HOSTS.items()}


def lookup(name):
    if name not in HOSTS:
        raise ValueError('Unknown office fixture')
    wire_name = b''.join(bytes([len(part)])+part.encode() for part in
                         (name+'.office.range.test').split('.'))+b'\0'
    ident = os.urandom(2)  # Protocol identifier, not behavioural randomness.
    packet = ident+struct.pack('!5H', 0x0100, 1, 0, 0, 0)+wire_name+struct.pack('!HH', 1, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        sock.connect(('scenario-sink.internal', 1053))
        sock.send(packet)
        reply = sock.recv(512)
    if (len(reply) != len(packet)+16 or reply[:2] != ident or reply[3] & 15
            or reply[6:8] != b'\0\x01' or reply[12:len(packet)] != packet[12:]):
        raise RuntimeError('Invalid office DNS fixture reply')
    pointer, kind, family, ttl, length, ip = struct.unpack('!HHHIH4s', reply[-16:])
    if (pointer, kind, family, length) != (0xc00c, 1, 1, 4):
        raise RuntimeError('Invalid office DNS answer')
    return socket.inet_ntoa(ip)

#!/usr/bin/env python3
import glob, hmac, json, shutil, socket, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = '/opt/sysmon-dashboard'
KEY = open('/etc/sysmon_api_key').read().strip()

def cpu_percent():
    def read():
        v = list(map(int, open('/proc/stat').readline().split()[1:]))
        return sum(v), v[3] + v[4]
    t1, i1 = read(); time.sleep(0.5); t2, i2 = read()
    return round(100 * (1 - (i2 - i1) / max(t2 - t1, 1)), 1)

def mem_percent():
    m = {}
    for line in open('/proc/meminfo'):
        k, v = line.split(':'); m[k] = int(v.split()[0])
    return round(100 * (1 - m['MemAvailable'] / m['MemTotal']), 1)

def disk_percent(path):
    try:
        u = shutil.disk_usage(path)
        return round(100 * u.used / u.total, 1)
    except Exception:
        return None

def service(name):
    return subprocess.run(['systemctl', 'is-active', '--quiet', name]).returncode == 0

def last_logs(n=15):
    files = sorted(glob.glob('/var/log/sysmon/health_*.log'))
    return open(files[-1]).read().splitlines()[-n:] if files else []

def uptime():
    s = int(float(open('/proc/uptime').read().split()[0]))
    return '%dh %dm' % (s // 3600, s % 3600 // 60)

def metrics():
    return {
        'host': socket.gethostname(),
        'time': time.strftime('%F %T'),
        'uptime': uptime(),
        'cpu': cpu_percent(),
        'mem': mem_percent(),
        'disk': disk_percent('/'),
        'vol': disk_percent('/var/log/sysmon'),
        'services': {'ssh': service('ssh'), 'cron': service('cron')},
        'logs': last_logs(),
    }

class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send(200, open(BASE + '/index.html', 'rb').read(), 'text/html; charset=utf-8')
        elif self.path == '/api/metrics':
            if not hmac.compare_digest(self.headers.get('X-API-Key', ''), KEY):
                with open('/var/log/sysmon/dashboard.log', 'a') as f:
                    f.write('%s [WARN] invalid API key from %s\n' % (time.strftime('%F %T'), self.client_address[0]))
                self.send(401, b'{"error":"invalid api key"}', 'application/json')
                return
            self.send(200, json.dumps(metrics()).encode(), 'application/json')
        else:
            self.send(404, b'not found', 'text/plain')

    def log_message(self, *a):
        pass

ThreadingHTTPServer(('0.0.0.0', 8080), H).serve_forever()

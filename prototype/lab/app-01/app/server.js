// VulnCastle - Intentionally Vulnerable API (Educational Purpose Only)
// nosemgrep
const express = require('express');
const http = require('http');
const { execSync } = require('child_process');
const fs = require('fs');
const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
// Emit request evidence without changing the intentionally vulnerable routes.
app.use((req, res, next) => {
  const started = Date.now();
  res.on('finish', () => console.log(JSON.stringify({
    time: new Date().toISOString(), source: req.ip, method: req.method,
    url: req.originalUrl, status: res.statusCode, duration_ms: Date.now() - started
  })));
  next();
});

// Fake user database (IDOR vulnerability)
const users = {
  1: { id: 1, name: "Alice Admin", role: "admin", email: "alice@acme-corp.local", ssn: "123-45-6789", salary: 150000 },
  2: { id: 2, name: "Bob Builder", role: "user", email: "bob@acme-corp.local", ssn: "987-65-4321", salary: 85000 },
  3: { id: 3, name: "Charlie Coder", role: "user", email: "charlie@acme-corp.local", ssn: "456-78-9012", salary: 95000 },
  4: { id: 4, name: "Service Account", role: "service", api_key: "sk-vuln-4f8a2b1c9d3e7f6a", internal_notes: "Has access to db-01 and file-01" },
};

// IDOR: No authorization check - any user ID accessible
app.get('/api/users/:id', (req, res) => {
  const user = users[req.params.id];
  if (user) {
    res.json(user);
  } else {
    res.status(404).json({ error: "User not found" });
  }
});

// List all users (information disclosure)
app.get('/api/users', (req, res) => {
  res.json(Object.values(users));
});

// SSRF vulnerability: fetch internal resources
app.get('/api/fetch', (req, res) => {
  const url = req.query.url;
  if (!url) {
    return res.status(400).json({ error: "url parameter required" });
  }
  // Vulnerable: no URL validation, can access internal services
  http.get(url, (proxyRes) => {
    let data = '';
    proxyRes.on('data', chunk => data += chunk);
    proxyRes.on('end', () => res.send(data));
  }).on('error', (err) => {
    res.status(500).json({ error: err.message });
  });
});

// Command injection via diagnostics endpoint
app.post('/api/diagnostics', (req, res) => {
  const target = req.body.target;
  if (!target) {
    return res.status(400).json({ error: "target required" });
  }
  try {
    // Vulnerable: direct command injection
    const output = execSync(`nslookup ${target}`, { timeout: 5000 }).toString();
    res.json({ result: output });
  } catch (err) {
    res.json({ result: err.stdout ? err.stdout.toString() : err.message });
  }
});

// Path traversal via file read
app.get('/api/files', (req, res) => {
  const filename = req.query.name || 'readme.txt';
  // Vulnerable: no path sanitization
  try {
    const content = fs.readFileSync('/opt/api/data/' + filename, 'utf8');
    res.json({ filename, content });
  } catch (err) {
    res.status(404).json({ error: "File not found" });
  }
});

// Health check exposes internal info
app.get('/api/health', (req, res) => {
  res.json({
    status: "ok",
    hostname: require('os').hostname(),
    platform: process.platform,
    arch: process.arch,
    uptime: process.uptime(),
    env: process.env.NODE_ENV || "development",
    internal_services: {
      database: "db-01.internal:3306",
      fileserver: "file-01.internal:445",
      redis: "admin-01.internal:6379"
    }
  });
});

app.get('/', (req, res) => {
  res.json({
    name: "ACME Corp Internal API",
    version: "1.0.0",
    endpoints: ["/api/users", "/api/users/:id", "/api/fetch?url=", "/api/diagnostics", "/api/files?name=", "/api/health"]
  });
});

app.listen(3000, '0.0.0.0', () => {
  console.log('API server running on port 3000');
});

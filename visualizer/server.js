'use strict';

const dgram  = require('dgram');
const http   = require('http');
const fs     = require('fs');
const path   = require('path');
const { WebSocketServer } = require('ws');

// ── Config ────────────────────────────────────────────────────────────────────
const UDP_PORT   = parseInt(process.env.UDP_PORT  || '5152');
const HTTP_PORT  = parseInt(process.env.HTTP_PORT || '3000');
const MAX_HISTORY = 2_000_000; // max stored packets

// ── Packet layout ────────────────────────────────────────────────────────────
//  offset  size  field
//       0     8  thread_id          (uint64 LE)
//       8     8  start_time_µs      (uint64 LE)
//      16     8  end_time_µs        (uint64 LE)
//      24     8  elapsed_time_µs    (uint64 LE)
//      32     8  call_stack_size    (uint64 LE)
//      40  1024  call_stack         (char[])
const STRUCT_SIZE = 40 + 1024; // 1064 bytes

// ── State ────────────────────────────────────────────────────────────────────
const history = [];   // all packets (capped at MAX_HISTORY)

// ── Packet parser ─────────────────────────────────────────────────────────────
function parsePacket(buf) {
  if (buf.length < STRUCT_SIZE) return null;
  try {
    const thread_id  = buf.readBigUInt64LE(0).toString();
    const startBig   = buf.readBigUInt64LE(8);
    const endBig     = buf.readBigUInt64LE(16);
    const elapsedBig = buf.readBigUInt64LE(24);
    const stackSize  = Number(buf.readBigUInt64LE(32));

    // Raw timestamps fit safely in JS Number (float64 mantissa = 53 bits,
    // Unix µs ≈ 1.77×10¹⁵ < 2⁵³ ≈ 9×10¹⁵). No server-side normalisation
    // needed — the client subtracts globalMinTime for display.
    const start   = Number(startBig);
    const end     = Number(endBig);
    const elapsed = Number(elapsedBig);

    const len        = Math.min(stackSize || 1024, 1024);
    const stackSlice = buf.subarray(40, 40 + len);
    const nullAt     = stackSlice.indexOf(0);
    const call_stack = stackSlice
      .subarray(0, nullAt >= 0 ? nullAt : len)
      .toString('utf8')
      .trim();

    if (!call_stack) return null;
    return { thread_id, start, end, elapsed, call_stack };
  } catch {
    return null;
  }
}

// ── HTTP server (static files) ────────────────────────────────────────────────
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
};

const httpServer = http.createServer((req, res) => {
  const rel      = req.url === '/' ? '/index.html' : req.url;
  const filePath = path.join(__dirname, 'public', rel);

  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end('404 Not Found'); return; }
    const mime = MIME[path.extname(filePath)] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  });
});

// ── WebSocket server ──────────────────────────────────────────────────────────
const wss = new WebSocketServer({ server: httpServer });

wss.on('connection', ws => {
  console.log('[WS] Client connected — sending history (%d packets)', history.length);

  // Stream history in chunks to avoid blocking
  const CHUNK = 1000;
  let i = 0;
  function sendChunk() {
    if (ws.readyState !== ws.OPEN) return;
    if (i >= history.length) return;
    ws.send(JSON.stringify({ type: 'batch', packets: history.slice(i, i + CHUNK) }));
    i += CHUNK;
    setImmediate(sendChunk);
  }
  sendChunk();
});

// ── Live broadcast (batched every 50 ms) ─────────────────────────────────────
let pending = [];

setInterval(() => {
  if (pending.length === 0) return;
  const batch = pending;
  pending = [];
  const msg = JSON.stringify({ type: 'batch', packets: batch });
  for (const ws of wss.clients) {
    if (ws.readyState === ws.OPEN) ws.send(msg);
  }
}, 50);

// ── UDP socket ────────────────────────────────────────────────────────────────
const udp = dgram.createSocket({ type: 'udp4', recvBufferSize: 32 * 1024 * 1024 });

let _rawCount = 0;
let _okCount  = 0;

udp.on('message', (buf, rinfo) => {
  _rawCount++;

  // First few packets: always dump raw info so problems are obvious
  if (_rawCount <= 5) {
    console.log(`[UDP] pkt #${_rawCount} from ${rinfo.address}:${rinfo.port}  len=${buf.length}`);
    if (buf.length >= 40) {
      try {
        console.log(`      thread_id =${buf.readBigUInt64LE(0)}`);
        console.log(`      start     =${buf.readBigUInt64LE(8)}`);
        console.log(`      end       =${buf.readBigUInt64LE(16)}`);
        console.log(`      elapsed   =${buf.readBigUInt64LE(24)}`);
        console.log(`      stack_size=${buf.readBigUInt64LE(32)}`);
        const preview = buf.subarray(40, Math.min(40 + 80, buf.length));
        console.log(`      stack_raw =${JSON.stringify(preview.toString('utf8'))}`);
      } catch(e) { console.log('      (parse error:', e.message, ')'); }
    } else {
      console.log('      (too short for header)');
    }
  }

  // Periodic stats
  if (_rawCount % 1000 === 0) {
    console.log(`[UDP] received=${_rawCount}  parsed_ok=${_okCount}  dropped=${_rawCount-_okCount}`);
  }

  const pkt = parsePacket(buf);
  if (!pkt) return;
  _okCount++;
  pending.push(pkt);
  if (history.length < MAX_HISTORY) history.push(pkt);
});

udp.on('error', err => console.error('[UDP] Error:', err));

udp.bind(UDP_PORT, '0.0.0.0', () => {
  console.log(`[UDP ] Listening on 0.0.0.0:${UDP_PORT}`);
});

httpServer.listen(HTTP_PORT, () => {
  console.log(`[HTTP] Listening on http://localhost:${HTTP_PORT}`);
  console.log(`[INFO] Open http://localhost:${HTTP_PORT} in your browser`);
});

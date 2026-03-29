// Minimal UDP listener — no npm deps, no parsing logic.
// Run: node test-udp.js
// If your profiler sends anything at all to 5152, you'll see it here.
const dgram = require('dgram');

const sock = dgram.createSocket('udp4');

sock.on('error', err => {
  console.error('[ERROR]', err.message);
  process.exit(1);
});

sock.on('listening', () => {
  const { address, port } = sock.address();
  console.log(`Listening on UDP ${address}:${port}`);
  console.log('Waiting for packets... (Ctrl-C to stop)\n');
});

sock.on('message', (buf, rinfo) => {
  console.log(`Got ${buf.length} bytes from ${rinfo.address}:${rinfo.port}`);
  console.log('  hex (first 80 bytes):', buf.subarray(0, 80).toString('hex'));
  if (buf.length >= 40) {
    console.log('  thread_id :', buf.readBigUInt64LE(0).toString());
    console.log('  start µs  :', buf.readBigUInt64LE(8).toString());
    console.log('  end µs    :', buf.readBigUInt64LE(16).toString());
    console.log('  elapsed µs:', buf.readBigUInt64LE(24).toString());
    console.log('  stack_size:', buf.readBigUInt64LE(32).toString());
    console.log('  stack raw :', JSON.stringify(buf.subarray(40, Math.min(buf.length, 120)).toString('utf8')));
  }
  console.log('');
});

// Try binding — if port is in use, this will error.
sock.bind(5152, '0.0.0.0');

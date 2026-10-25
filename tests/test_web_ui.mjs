import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../physqed_q/web_assets/app.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../physqed_q/web_assets/index.html', import.meta.url), 'utf8');

function loadWorkbench() {
  const context = { document: { addEventListener() {} }, setTimeout, clearTimeout };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

function withUI() {
  const nodes = new Map();
  const context = loadWorkbench();
  context.document.getElementById = (id) => {
    if (!nodes.has(id)) nodes.set(id, {
      textContent: '', disabled: false, hidden: false, value: id === 'optimizer' ? 'adjacent' : '',
      classList: { add() {}, remove() {} },
      replaceChildren() {},
      append() {},
      listeners: new Map(),
      addEventListener(type, listener) { this.listeners.set(type, listener); },
      click() { this.clicked = true; this.listeners.get('click')?.(); },
    });
    return nodes.get(id);
  };
  context.document.createElement = (_tag) => ({
    textContent: '', className: '', style: {}, append() {}, setAttribute() {},
  });
  context.document.querySelectorAll = () => [];
  context.setTimeout = () => 0;
  context.clearTimeout = () => {};
  context.requests = [];
  context.fetch = (url, options) => new Promise((resolve) => context.requests.push({ url, options, resolve }));
  context.getUI = (id) => nodes.get(id);
  return context;
}

function respond(request, body, status = 200) {
  request.resolve({ ok: status < 400, status, json: async () => body });
}

test('import normalizes valid ordered CNOT without changing control and target', () => {
  const context = loadWorkbench();
  const actual = vm.runInContext(`normalizeCircuit({
    name: 'Control reversal', qubits: 2,
    gates: [{ gate: 'CNOT', qubits: [1, 0] }]
  })`, context);
  assert.deepEqual(JSON.parse(JSON.stringify(actual)), {
    name: 'Control reversal', qubits: 2,
    gates: [{ gate: 'CNOT', qubits: [1, 0] }],
  });
});

test('import rejects repeated qubits, unknown gates and over-budget input', () => {
  const context = loadWorkbench();
  for (const gates of [
    [{ gate: 'CNOT', qubits: [0, 0] }],
    [{ gate: 'RX', qubits: [0] }],
    Array.from({ length: 65 }, () => ({ gate: 'H', qubits: [0] })),
  ]) {
    context.candidate = { name: 'invalid', qubits: 2, gates };
    assert.throws(() => vm.runInContext('normalizeCircuit(candidate)', context));
  }
});

test('a slower older preset request cannot overwrite a newer choice', async () => {
  const context = loadWorkbench();
  const callbacks = new Map();
  const applied = [];
  context.fetch = (url) => new Promise((resolve) => callbacks.set(url, resolve));
  context.loadCircuit = (_data, options) => applied.push(options.preset);

  const oldRequest = vm.runInContext('loadPreset("optimize")', context);
  const newRequest = vm.runInContext('loadPreset("bell")', context);
  callbacks.get('/api/examples/bell')({ ok: true, json: async () => ({ circuit: { name: 'bell' } }) });
  await newRequest;
  callbacks.get('/api/examples/optimize')({ ok: true, json: async () => ({ circuit: { name: 'opt' } }) });
  await oldRequest;

  assert.deepEqual(applied, ['bell']);
});

test('old Lean success cannot turn a failed newer optimization green', async () => {
  const context = withUI();
  vm.runInContext('state.receipt = { receipt_sha256: "older" }', context);
  const lean = vm.runInContext('attestLean()', context);
  const compile = vm.runInContext('optimizeAndVerify()', context);
  respond(context.requests.find((r) => r.url === '/api/compile'), { error: 'rejected circuit' }, 422);
  await compile;
  assert.equal(context.getUI('status-title').textContent, 'Verification not obtained');
  respond(context.requests.find((r) => r.url === '/api/lean'), {
    attestation: { lean_theorem_checked: true, lean_gate_decoder_checked: true, lean_source_sha256: 'old' },
  });
  await lean;
  assert.equal(context.getUI('status-title').textContent, 'Verification not obtained');
  assert.equal(vm.runInContext('state.receipt', context), null);
});

test('old replay success cannot override newer compile failure', async () => {
  const context = withUI();
  vm.runInContext('state.receipt = { receipt_sha256: "older" }', context);
  const replay = vm.runInContext('replayReceipt()', context);
  const compile = vm.runInContext('optimizeAndVerify()', context);
  respond(context.requests.find((r) => r.url === '/api/compile'), { error: 'invalid input' }, 422);
  await compile;
  respond(context.requests.find((r) => r.url === '/api/verify'), {
    verification: { verified: true, rewrites_checked: 0 },
  });
  await replay;
  assert.equal(context.getUI('status-title').textContent, 'Verification not obtained');
  assert.equal(vm.runInContext('state.receipt', context), null);
});

test('old compile finally cannot enable Run during a newer compile', async () => {
  const context = withUI();
  const first = vm.runInContext('optimizeAndVerify()', context);
  vm.runInContext('dirty()', context);
  const second = vm.runInContext('optimizeAndVerify()', context);
  respond(context.requests[0], { error: 'stale failure' }, 422);
  await first;
  assert.equal(context.getUI('run-button').disabled, true);
  respond(context.requests[1], { error: 'new failure' }, 422);
  await second;
  assert.equal(context.getUI('run-button').disabled, false);
});

test('editing while Lean is pending invalidates that earlier reply', async () => {
  const context = withUI();
  vm.runInContext('state.receipt = { receipt_sha256: "old" }', context);
  const lean = vm.runInContext('attestLean()', context);
  vm.runInContext('dirty()', context);
  respond(context.requests[0], {
    attestation: { lean_theorem_checked: true, lean_gate_decoder_checked: true, lean_source_sha256: 'old' },
  });
  await lean;
  assert.equal(context.getUI('status-title').textContent, 'Awaiting verification');
  assert.equal(vm.runInContext('state.receipt', context), null);
});

test('keyboard-accessible import button invokes the native file picker', () => {
  const context = withUI();
  vm.runInContext('bindControls()', context);
  context.getUI('import-button').click();
  assert.equal(context.getUI('import-circuit').clicked, true);
});

test('optimizer uses a labeled native select with legacy default and opt-in choice', () => {
  // These markup contracts make the real browser expose a keyboard-operable named control.
  assert.match(html, /<label\b[^>]*for="optimizer"[^>]*>Optimization strategy<\/label>/);
  const select = html.match(/<select\b[^>]*id="optimizer"[^>]*>([\s\S]*?)<\/select>/);
  assert.ok(select, 'native optimizer select is present');
  const options = [...select[1].matchAll(/<option\b([^>]*)value="([^"]+)"([^>]*)>([^<]+)<\/option>/g)];
  assert.deepEqual(options.map((option) => option[2]), ['adjacent', 'commuting']);
  assert.ok(!/\bselected\b/.test(options[1][1] + options[1][3]), 'commuting is not selected by default');
  assert.doesNotMatch(select[0], /\bdisabled\b|tabindex="-1"/);
});

test('optimization submits the chosen strategy and does not claim Lean verification', async () => {
  for (const optimizer of ['adjacent', 'commuting']) {
    const context = withUI();
    vm.runInContext('bindControls()', context);
    context.document.getElementById('optimizer').value = optimizer;
    const compile = vm.runInContext('optimizeAndVerify()', context);
    const request = context.requests[0];
    assert.equal(request.url, '/api/compile');
    assert.equal(JSON.parse(request.options.body).optimizer, optimizer);
    const circuit = { name: 'Empty', qubits: 2, gates: [] };
    const metrics = { gates: 0, depth: 0, t_gates: 0, two_qubit_gates: 0 };
    respond(request, { receipt: {
      schema: `physqed-q-exact-receipt-v${optimizer === 'commuting' ? 2 : 1}`,
      input: circuit, optimized: circuit, steps: [],
      metrics: { input: metrics, optimized: metrics },
      operator_sha256: 'a'.repeat(64), receipt_sha256: 'b'.repeat(64),
      scope: { kernel: 'exact operator equality in Q(sqrt(2),i); at most four qubits',
        lean_kernel_verified: false, hardware_verified: false,
        quantum_advantage_demonstrated: false, integrity_not_authenticity: true,
        ...(optimizer === 'commuting' ? { optimizer: 'commuting-disjoint-v1' } : {}) },
    },
      verification: { verified: true, rewrites_checked: 0, lean_kernel_verified: false } });
    await compile;
    assert.equal(context.getUI('status-title').textContent, 'Exact equivalence verified');
    assert.equal(vm.runInContext('state.attestation', context), null);
    assert.match(context.getUI('lean-status').textContent, /optional/);
    assert.equal(context.getUI('lean-button').disabled, false, 'eligible receipt permits a separate Lean check');
  }
});

test('changing strategy invalidates a pending compile and its earlier Lean evidence', async () => {
  const context = withUI();
  vm.runInContext('bindControls()', context);
  const compile = vm.runInContext('optimizeAndVerify()', context);
  vm.runInContext('state.attestation = { lean_theorem_checked: true }', context);
  context.document.getElementById('optimizer').value = 'commuting';
  const change = context.getUI('optimizer').listeners.get('change');
  assert.equal(typeof change, 'function');
  change();
  assert.equal(vm.runInContext('state.attestation', context), null);
  assert.equal(context.getUI('status-title').textContent, 'Awaiting verification');
  respond(context.requests[0], { verification: { verified: true, rewrites_checked: 0 }, receipt: {} });
  await compile;
  assert.equal(context.getUI('status-title').textContent, 'Awaiting verification');
  assert.equal(vm.runInContext('state.receipt', context), null);
});

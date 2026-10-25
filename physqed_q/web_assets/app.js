"use strict";

/* PHYSQED-Q visual workbench. This file never calculates a quantum proof:
   status changes to verified only after the Python HTTP API confirms replay. */

const GATE_TYPES = ["H", "X", "Z", "S", "SDG", "T", "TDG", "CNOT", "CZ", "SWAP"];
const TWO_QUBIT = new Set(["CNOT", "CZ", "SWAP"]);
const state = {
  circuit: { name: "Untitled circuit", qubits: 2, gates: [] },
  chosenGate: "H", selectedIndex: -1, revision: 0,
  receipt: null, attestation: null, activePreset: "optimize", presetRequest: 0,
  proofEpoch: 0,
};
const $ = (id) => document.getElementById(id);

function element(tag, className, label) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (label !== undefined) node.textContent = String(label);
  return node;
}

function message(error) {
  const toast = $("toast");
  toast.textContent = String(error);
  toast.hidden = false;
  clearTimeout(message.timeout);
  message.timeout = setTimeout(() => { toast.hidden = true; }, 6500);
}

function status(kind, title, detail) {
  const card = $("verification-card");
  card.classList.remove("running", "verified", "failed");
  if (kind !== "idle") card.classList.add(kind);
  $("status-mark").textContent = ({ idle: "○", running: "⋯", verified: "✓", failed: "!" })[kind];
  $("status-title").textContent = title;
  $("status-detail").textContent = detail;
}

function resetResults() {
  state.receipt = null;
  state.attestation = null;
  status("idle", "Awaiting verification", "Run the exact optimizer to check this circuit.");
  for (const name of ["metric-before", "metric-after", "metric-depth", "metric-t", "reduction-value"]) {
    $(name).textContent = "—";
  }
  $("metrics-label").textContent = "PENDING";
  $("optimized-label").textContent = "NOT YET COMPUTED";
  $("operator-digest").textContent = "Pending computation";
  $("rewrite-count").textContent = "0 REWRITES";
  $("rewrite-list").replaceChildren(element("li", "trace-placeholder", "No rewrite trace yet"));
  $("optimized-board").replaceChildren(element("div", "empty-result", "The verified output diagram will appear here."));
  $("recheck-button").disabled = true;
  $("lean-button").disabled = true;
  $("download-receipt").disabled = true;
  $("lean-status").textContent = "Lean attestation is optional and restricted to two-qubit circuits with at most 16 gates in each word.";
}

function dirty() {
  state.revision += 1;
  state.presetRequest += 1;
  state.proofEpoch += 1;
  resetResults();
  $("run-button").disabled = false;
}

function drawBoard(container, circuit, { select = false } = {}) {
  container.replaceChildren();
  const grid = element("div", "circuit-grid");
  const n = circuit.qubits;
  const gates = circuit.gates;
  const slots = Math.max(1, gates.length);
  grid.style.gridTemplateColumns = `minmax(80px,95px) repeat(${slots}, 72px)`;
  grid.style.gridTemplateRows = `repeat(${n}, 60px)`;

  for (let q = 0; q < n; q += 1) {
    const label = element("div", "wire-label");
    label.textContent = `q${q}`;
    const ket = element("span", "", "|0⟩");
    label.append(ket);
    label.style.gridRow = String(q + 1);
    grid.append(label);
    for (let k = 0; k < slots; k += 1) {
      const wire = element("div", "wire-cell");
      wire.style.gridRow = String(q + 1);
      wire.style.gridColumn = String(k + 2);
      grid.append(wire);
    }
  }

  gates.forEach((gate, index) => {
    const qs = gate.qubits;
    const two = qs.length === 2;
    if (two) {
      const connector = element("div", "connector");
      connector.style.gridColumn = String(index + 2);
      connector.style.gridRow = `${Math.min(...qs) + 1} / ${Math.max(...qs) + 2}`;
      grid.append(connector);
    }
    qs.forEach((q, j) => {
      const classes = ["gate-pill"];
      if (two) classes.push("two-qubit");
      if (select && state.selectedIndex === index) classes.push("active");
      let label = gate.gate;
      if (gate.gate === "CNOT") {
        label = j === 0 ? "●" : "⊕";
        classes.push(j === 0 ? "control" : "target");
      } else if (gate.gate === "CZ") {
        label = "●";
        classes.push("control");
      } else if (gate.gate === "SWAP") {
        label = "×";
        classes.push("swap");
      }
      const pill = element("button", classes.join(" "), label);
      pill.type = "button";
      pill.title = `${index + 1}. ${gate.gate}(${qs.join(", ")})`;
      pill.setAttribute("aria-label", pill.title);
      pill.style.gridColumn = String(index + 2);
      pill.style.gridRow = String(q + 1);
      if (select) pill.addEventListener("click", () => { state.selectedIndex = index; renderCircuit(); });
      else pill.disabled = true;
      grid.append(pill);
    });
  });

  if (gates.length === 0) grid.append(element("div", "empty-circuit", "No gates — identity circuit"));
  container.append(grid);
}

function gateText(gate) { return `${gate.gate}(${gate.qubits.join(",")})`; }

function renderCircuit() {
  drawBoard($("source-board"), state.circuit, { select: true });
  $("sequence-count").textContent = `${state.circuit.gates.length} operation${state.circuit.gates.length === 1 ? "" : "s"}`;
  const list = $("gate-sequence");
  list.replaceChildren();
  state.circuit.gates.forEach((gate, index) => {
    const item = element("li", "sequence-item" + (state.selectedIndex === index ? " chosen" : ""));
    item.append(element("span", "sequence-number", String(index + 1).padStart(2, "0")));
    const name = element("span", "sequence-name", gateText(gate));
    name.title = gateText(gate);
    item.append(name);
    const commands = [
      { name: "Move left", glyph: "←", allowed: index > 0, handler: () => shiftGate(index, -1) },
      { name: "Move right", glyph: "→", allowed: index < state.circuit.gates.length - 1, handler: () => shiftGate(index, 1) },
      { name: "Remove", glyph: "×", allowed: true, handler: () => deleteGate(index) },
    ];
    commands.forEach((c) => {
      const button = element("button", "seq-action" + (c.name === "Remove" ? " remove" : ""), c.glyph);
      button.type = "button";
      button.disabled = !c.allowed;
      button.title = `${c.name} gate ${index + 1}`;
      button.setAttribute("aria-label", button.title);
      button.addEventListener("click", c.handler);
      item.append(button);
    });
    list.append(item);
  });
  if (state.circuit.gates.length === 0) list.append(element("li", "sequence-empty", "Choose a gate and press Add gate to begin."));
}

function shiftGate(index, change) {
  const next = index + change;
  const gates = state.circuit.gates;
  if (next < 0 || next >= gates.length) return;
  [gates[index], gates[next]] = [gates[next], gates[index]];
  state.selectedIndex = next;
  dirty();
  renderCircuit();
}

function deleteGate(index) {
  state.circuit.gates.splice(index, 1);
  state.selectedIndex = Math.min(index, state.circuit.gates.length - 1);
  dirty();
  renderCircuit();
}

function populateQubits() {
  const a = $("gate-qubit-a");
  const b = $("gate-qubit-b");
  const oldA = Number(a.value);
  const oldB = Number(b.value);
  a.replaceChildren(); b.replaceChildren();
  for (let i = 0; i < state.circuit.qubits; i += 1) {
    a.append(new Option(`q${i}`, String(i)));
    b.append(new Option(`q${i}`, String(i)));
  }
  a.value = String(oldA < state.circuit.qubits ? oldA : 0);
  b.value = String(oldB < state.circuit.qubits && oldB !== Number(a.value)
    ? oldB : (Number(a.value) === 0 ? 1 : 0));
  if (state.circuit.qubits === 1) b.value = "0";
  const isDouble = TWO_QUBIT.has(state.chosenGate);
  $("second-qubit-field").hidden = !isDouble;
  $("add-gate").disabled = isDouble && state.circuit.qubits < 2;
}

function renderPalette() {
  const palette = $("gate-palette");
  palette.replaceChildren();
  GATE_TYPES.forEach((gate) => {
    const button = element("button", "gate-choice" + (TWO_QUBIT.has(gate) ? " double" : "") + (state.chosenGate === gate ? " selected" : ""), gate);
    button.type = "button";
    button.setAttribute("aria-pressed", state.chosenGate === gate ? "true" : "false");
    button.title = `Select ${gate} gate`;
    button.addEventListener("click", () => {
      state.chosenGate = gate;
      renderPalette();
      populateQubits();
    });
    palette.append(button);
  });
}

function addGate() {
  if (state.circuit.gates.length >= 64) { message("The exact Python engine supports up to 64 gates per circuit."); return; }
  const first = Number($("gate-qubit-a").value);
  const two = TWO_QUBIT.has(state.chosenGate);
  const second = Number($("gate-qubit-b").value);
  if (two && (first === second || state.circuit.qubits < 2)) {
    message("A two-qubit gate requires two different qubit indices.");
    return;
  }
  state.circuit.gates.push({ gate: state.chosenGate, qubits: two ? [first, second] : [first] });
  state.selectedIndex = state.circuit.gates.length - 1;
  dirty();
  renderCircuit();
}

function normalizeCircuit(data) {
  const candidate = data && data.input && data.schema ? data.input : data;
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate) ||
      typeof candidate.name !== "string" || !candidate.name.trim() || candidate.name.length > 120 ||
      !Number.isInteger(candidate.qubits) || candidate.qubits < 1 || candidate.qubits > 4 ||
      !Array.isArray(candidate.gates) || candidate.gates.length > 64) {
    throw new Error("The file must contain a named circuit with 1–4 qubits and up to 64 gates.");
  }
  const gates = candidate.gates.map((gate, i) => {
    if (!gate || !GATE_TYPES.includes(gate.gate) || !Array.isArray(gate.qubits)) {
      throw new Error(`Unsupported gate at position ${i + 1}.`);
    }
    const width = TWO_QUBIT.has(gate.gate) ? 2 : 1;
    if (gate.qubits.length !== width || gate.qubits.some((q) => !Number.isInteger(q) || q < 0 || q >= candidate.qubits) ||
        new Set(gate.qubits).size !== width) {
      throw new Error(`Invalid qubit positions at gate ${i + 1}.`);
    }
    return { gate: gate.gate, qubits: [...gate.qubits] };
  });
  return { name: candidate.name, qubits: candidate.qubits, gates };
}

function loadCircuit(data, { preset = null } = {}) {
  state.circuit = normalizeCircuit(data);
  state.selectedIndex = -1;
  state.activePreset = preset;
  $("circuit-name").value = state.circuit.name;
  $("qubit-count").value = String(state.circuit.qubits);
  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.classList.toggle("active", button.dataset.preset === preset);
  });
  dirty();
  populateQubits();
  renderCircuit();
}

async function loadPreset(name) {
  const request = ++state.presetRequest;
  try {
    const response = await fetch(`/api/examples/${name}`);
    const data = await response.json();
    if (request !== state.presetRequest) return;
    if (!response.ok) throw new Error(data.error || "Could not load example");
    loadCircuit(data.circuit, { preset: name });
  } catch (error) {
    if (request !== state.presetRequest) return;
    message(`Unable to load ${name} example: ${error.message}`);
  }
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function displayReceipt(receipt) {
  const m = receipt.metrics;
  $("metric-before").textContent = m.input.gates;
  $("metric-after").textContent = m.optimized.gates;
  $("metric-depth").textContent = `${m.input.depth} → ${m.optimized.depth}`;
  $("metric-t").textContent = `${m.input.t_gates} → ${m.optimized.t_gates}`;
  $("metrics-label").textContent = "EXACTLY CHECKED";
  const reduction = m.input.gates === 0 ? 0 : 100 * (m.input.gates - m.optimized.gates) / m.input.gates;
  $("reduction-value").textContent = `${Math.round(reduction)}% fewer gates`;
  $("optimized-label").textContent = `${m.optimized.gates} GATES`;
  drawBoard($("optimized-board"), receipt.optimized);
  $("operator-digest").textContent = receipt.operator_sha256;
  $("rewrite-count").textContent = `${receipt.steps.length} REWRITE${receipt.steps.length === 1 ? "" : "S"}`;
  const trace = $("rewrite-list");
  trace.replaceChildren();
  receipt.steps.forEach((step, index) => {
    const line = element("li");
    line.append(element("span", "rule-name", `${String(index + 1).padStart(2, "0")}  ${step.rule}`));
    line.append(element("span", "rewrite-index", `at gate ${step.index + 1}`));
    trace.append(line);
  });
  if (!receipt.steps.length) trace.append(element("li", "trace-placeholder", "Already in normal form. The exact full operator was checked."));
  $("download-receipt").disabled = false;
  $("recheck-button").disabled = false;
  $("lean-button").disabled = !(receipt.input.qubits === 2 &&
    receipt.input.gates.length <= 16 && receipt.optimized.gates.length <= 16);
}

async function optimizeAndVerify() {
  const revision = state.revision;
  const epoch = ++state.proofEpoch;
  resetResults();
  $("run-button").disabled = true;
  status("running", "Checking exact operators…", "Applying permitted rewrites and independently replaying the receipt.");
  try {
    const result = await api("/api/compile", { circuit: state.circuit });
    if (revision !== state.revision || epoch !== state.proofEpoch) return;
    if (result.verification.verified !== true) throw new Error("The server did not verify the result.");
    state.receipt = result.receipt;
    displayReceipt(result.receipt);
    status("verified", "Exact equivalence verified", `${result.verification.rewrites_checked} rewrites replayed. All complete operator columns agree.`);
  } catch (error) {
    if (revision !== state.revision || epoch !== state.proofEpoch) return;
    resetResults();
    status("failed", "Verification not obtained", error.message);
    message(error.message);
  } finally {
    if (revision === state.revision && epoch === state.proofEpoch) $("run-button").disabled = false;
  }
}

async function replayReceipt() {
  if (!state.receipt) return;
  const receipt = state.receipt;
  const revision = state.revision;
  const epoch = ++state.proofEpoch;
  $("recheck-button").disabled = true;
  status("running", "Replaying receipt…", "Checking every recorded rewrite against the exact operator.");
  try {
    const result = await api("/api/verify", { receipt });
    if (revision !== state.revision || epoch !== state.proofEpoch || state.receipt !== receipt) return;
    if (result.verification.verified !== true) throw new Error("The independent replay did not verify.");
    status("verified", "Independent replay passed", `${result.verification.rewrites_checked} rewrites rechecked against exact operators.`);
  } catch (error) {
    if (revision !== state.revision || epoch !== state.proofEpoch || state.receipt !== receipt) return;
    state.receipt = null;
    resetResults();
    status("failed", "Receipt rejected", error.message);
    message(error.message);
  } finally {
    if (revision === state.revision && epoch === state.proofEpoch) {
      $("recheck-button").disabled = !state.receipt;
    }
  }
}

async function attestLean() {
  if (!state.receipt) return;
  const receipt = state.receipt;
  const revision = state.revision;
  const epoch = ++state.proofEpoch;
  $("lean-button").disabled = true;
  $("lean-status").textContent = "Running the separate Lean 4.24.0 kernel check…";
  try {
    const data = await api("/api/lean", { receipt });
    if (revision !== state.revision || epoch !== state.proofEpoch || state.receipt !== receipt) return;
    if (data.attestation.lean_theorem_checked !== true || data.attestation.lean_gate_decoder_checked !== true) {
      throw new Error("Lean did not return a valid v2 attestation.");
    }
    state.attestation = data.attestation;
    $("lean-status").textContent = `Lean theorem checked; separate v2 attestation SHA-256: ${data.attestation.lean_source_sha256}`;
    status("verified", "Python + Lean checks passed", "Exact Python replay and a separate kernel-checked two-qubit Lean theorem passed.");
  } catch (error) {
    if (revision !== state.revision || epoch !== state.proofEpoch || state.receipt !== receipt) return;
    $("lean-status").textContent = `Lean check unavailable or rejected: ${error.message}. Python receipt status is independent.`;
    message(`Lean: ${error.message}`);
  } finally {
    if (revision === state.revision && epoch === state.proofEpoch && state.receipt === receipt) {
      $("lean-button").disabled = false;
    }
  }
}

function downloadJson(name, data) {
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function bindControls() {
  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => loadPreset(button.dataset.preset));
  });
  $("circuit-name").addEventListener("input", (event) => {
    state.circuit.name = event.target.value;
    state.activePreset = null;
    dirty();
  });
  $("qubit-count").addEventListener("change", (event) => {
    const n = Number(event.target.value);
    state.circuit.qubits = n;
    state.circuit.gates = state.circuit.gates.filter((gate) => gate.qubits.every((q) => q < n));
    state.selectedIndex = -1;
    state.activePreset = null;
    dirty();
    populateQubits();
    renderCircuit();
  });
  $("add-gate").addEventListener("click", addGate);
  $("reset-circuit").addEventListener("click", () => loadCircuit({ name: "Untitled circuit", qubits: 2, gates: [] }));
  $("run-button").addEventListener("click", optimizeAndVerify);
  $("recheck-button").addEventListener("click", replayReceipt);
  $("lean-button").addEventListener("click", attestLean);
  $("download-receipt").addEventListener("click", () => {
    if (state.receipt) downloadJson("physqed-q-exact-receipt.json", state.receipt);
  });
  $("import-button").addEventListener("click", () => $("import-circuit").click());
  $("export-circuit").addEventListener("click", () => downloadJson("physqed-q-circuit.json", state.circuit));
  $("import-circuit").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 256 * 1024) throw new Error("The circuit file exceeds 256 KiB.");
      loadCircuit(JSON.parse(await file.text()));
    } catch (error) {
      message(`Import rejected: ${error.message}`);
    } finally {
      event.target.value = "";
    }
  });
}

function init() {
  renderPalette();
  populateQubits();
  bindControls();
  resetResults();
  renderCircuit();
  loadPreset("optimize");
}

document.addEventListener("DOMContentLoaded", init);

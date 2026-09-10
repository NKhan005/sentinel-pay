const API_BASE = 'http://localhost:8000';

let currentRecords = [];
let chaosModeActive = false;
let selectedRecord = null;
let activePardonTxn = null;

/* Toast Notifications */
const ICONS = {
  success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4 12 14.01l-3-3"/></svg>',
  error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>'
};

function showToast(message, type = 'info', duration = 4000) {
  const stack = document.getElementById('toastStack');
  if (!stack) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon" aria-hidden="true">${ICONS[type] || ICONS.info}</span>
    <div class="toast-body">${message}</div>
    <button class="toast-close" aria-label="Dismiss">&times;</button>
  `;
  stack.appendChild(toast);

  const dismiss = () => toast.remove();
  const closeBtn = toast.querySelector('.toast-close');
  if (closeBtn) closeBtn.addEventListener('click', dismiss);
  setTimeout(dismiss, duration);
}

/* Clipboard Helper */
async function copyToClipboard(text, btnEl) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) { /* fallback */ }
    document.body.removeChild(ta);
  }
  if (btnEl) {
    btnEl.classList.add('copied');
    setTimeout(() => btnEl.classList.remove('copied'), 1200);
  }
  showToast('Copied to clipboard.', 'success', 1800);
}

/* Tab Navigation */
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    const targetView = tab.getAttribute('data-view');
    const panel = document.getElementById(`view-${targetView}`);
    if (panel) panel.classList.add('active');

    if (targetView === 'vault') {
      fetchDlqRecords();
    }
    if (targetView === 'analytics') {
      updateAnalytics(currentRecords);
    }
  });
});

/* Policy Sliders */
const sliderMaxRetries = document.getElementById('sliderMaxRetries');
if (sliderMaxRetries) {
  sliderMaxRetries.addEventListener('input', (e) => {
    const el = document.getElementById('valMaxRetries');
    if (el) el.innerText = `${e.target.value} Attempts`;
  });
}

const sliderBackoff = document.getElementById('sliderBackoff');
if (sliderBackoff) {
  sliderBackoff.addEventListener('input', (e) => {
    const el = document.getElementById('valBackoff');
    if (el) el.innerText = `${e.target.value} Minutes`;
  });
}

/* Audit CSV Trigger */
const exportBtn = document.getElementById('exportCsvBtn');
if (exportBtn) {
  exportBtn.addEventListener('click', () => {
    appendLogEntry('> [AUDIT EXPORT]: RBI-compliant dunning trace downloaded.', 'system');
    showToast('Audit CSV export initiated.', 'success');
  });
}

/* App Initialization */
document.addEventListener('DOMContentLoaded', () => {
  renderSwitchPlaceholders();
  fetchBankHealth();
  fetchDlqRecords();
  fetchComplianceHealth();
});

function renderSwitchPlaceholders() {
  const grid = document.getElementById('switchGrid');
  if (!grid) return;
  const banks = [
    { name: 'HDFC Bank UPI Switch', rail: 'UPI', sr: '98.8%', lat: '110ms', st: 'operational' },
    { name: 'SBI Core Switch', rail: 'IMPS/UPI', sr: '78.4%', lat: '940ms', st: 'degraded' },
    { name: 'ICICI NetBanking', rail: 'NB', sr: '99.1%', lat: '140ms', st: 'operational' },
    { name: 'NPCI Central Switch', rail: 'UPI', sr: '99.9%', lat: '85ms', st: 'operational' },
    { name: 'Axis Card Gateway', rail: 'CARD', sr: '94.2%', lat: '190ms', st: 'operational' }
  ];
  grid.innerHTML = '';
  banks.forEach(b => {
    const node = document.createElement('div');
    node.className = `switch-node ${b.st}`;
    node.innerHTML = `
      <div class="node-name"><span class="dot" aria-hidden="true"></span>${b.name}</div>
      <div class="node-sub">
        <span>${b.rail} &bull; ${b.sr} SR</span>
        <span>${b.lat}</span>
      </div>
    `;
    grid.appendChild(node);
  });
}

async function fetchBankHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/bank-switch-health`);
    if (!res.ok) return;
    const switches = await res.json();
    const grid = document.getElementById('switchGrid');
    if (!grid || !switches.length) return;
    grid.innerHTML = '';
    switches.forEach(sw => {
      const node = document.createElement('div');
      const st = (sw.status || '').toLowerCase();
      node.className = `switch-node ${st}`;
      node.innerHTML = `
        <div class="node-name"><span class="dot" aria-hidden="true"></span>${sw.bank_name}</div>
        <div class="node-sub">
          <span>${sw.rail} &bull; ${sw.success_rate}% SR</span>
          <span>${sw.avg_latency_ms}ms</span>
        </div>
      `;
      grid.appendChild(node);
    });
  } catch (err) {
    console.warn("Retaining default bank switches layout.");
  }
}

/* Compliance Health Index */
async function fetchComplianceHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/compliance-health-index`);
    if (!res.ok) return;
    const data = await res.json();

    const scoreEl = document.getElementById('complianceScore');
    const gradeEl = document.getElementById('complianceGrade');
    const subEl = document.getElementById('complianceSub');

    if (scoreEl) scoreEl.innerText = `${data.composite_score}%`;
    if (gradeEl) {
      gradeEl.innerText = `GRADE ${data.grade}`;
      gradeEl.className = `delta ${data.grade.startsWith('A') ? 'positive' : 'neutral'}`;
    }
    if (subEl) subEl.innerText = `${data.metrics.anti_harassment_adherence} Adherence`;
  } catch (err) {
    console.warn("Compliance health index offline, using default score.");
  }
}

/* Chaos Mode */
const chaosPill = document.getElementById('chaosToggleBtn');
if (chaosPill) {
  chaosPill.addEventListener('click', () => {
    chaosModeActive = !chaosModeActive;
    const label = chaosPill.querySelector('.chaos-label');
    if (chaosModeActive) {
      chaosPill.classList.add('active');
      chaosPill.setAttribute('aria-checked', 'true');
      if (label) label.innerHTML = 'Chaos: <strong>ACTIVE</strong>';
      appendLogEntry('> [CHAOS WARNING]: 429 Rate Limits & Network Jitter injection active.', 'system');
      showToast('Chaos mode active.', 'warning');
    } else {
      chaosPill.classList.remove('active');
      chaosPill.setAttribute('aria-checked', 'false');
      if (label) label.innerHTML = 'Chaos: <strong>OFF</strong>';
      appendLogEntry('> [CHAOS RESTORED]: Standard production routes restored.', 'system');
      showToast('Chaos mode disabled.', 'info');
    }
  });
}

/* Execute Recovery Batch */
const runBatchBtn = document.getElementById('runBatchBtn');
if (runBatchBtn) {
  runBatchBtn.addEventListener('click', async () => {
    runBatchBtn.disabled = true;
    runBatchBtn.innerText = "Processing...";
    const statusEl = document.getElementById('engineStatus');
    if (statusEl) statusEl.innerText = "STREAMING";

    try {
      const res = await fetch(`${API_BASE}/api/run-batch`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      currentRecords = data;
      renderDashboard(currentRecords);
      updateAnalytics(currentRecords);
      if (statusEl) statusEl.innerText = "ACTIVE";
      showToast(`Batch processed: ${data.length} transactions processed.`, 'success');
      fetchDlqRecords();
      fetchComplianceHealth();
    } catch (err) {
      showToast('Could not reach backend on localhost:8000.', 'error');
      if (statusEl) statusEl.innerText = "STANDBY";
    } finally {
      runBatchBtn.disabled = false;
      runBatchBtn.innerText = "Execute Recovery Batch";
    }
  });
}

/* Webhook Simulation */
const simulateWebhookBtn = document.getElementById('simulateWebhookBtn');
if (simulateWebhookBtn) {
  simulateWebhookBtn.addEventListener('click', async () => {
    simulateWebhookBtn.disabled = true;
    simulateWebhookBtn.innerText = "Ingesting...";

    const randomId = Math.floor(1000 + Math.random() * 9000);
    const mockPayload = {
      transaction_id: `pay_live_${randomId}`,
      customer_name: "Sneha Kulkarni",
      customer_phone: "+919876543210",
      amount: 3499.00,
      payment_method: "upi",
      error_code: chaosModeActive ? "GATEWAY_TIMEOUT_429" : "ISSUER_BANK_TIMEOUT",
      error_description: chaosModeActive ? "Simulated 429 rate limit" : "NPCI switch timeout",
      retry_count: chaosModeActive ? 3 : 0
    };

    try {
      const res = await fetch(`${API_BASE}/api/simulate-webhook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mockPayload)
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const response = await res.json();
      const decision = response.decision || response;

      if (decision && decision.transaction_id) {
        currentRecords.unshift(decision);
        renderDashboard(currentRecords, true);
        updateAnalytics(currentRecords);
        showToast(`Webhook ingested: ${decision.transaction_id}`, 'success');

        if (decision.stopping_rule_applied) {
          fetchDlqRecords();
        }
        fetchComplianceHealth();
      } else {
        showToast('Webhook processed.', 'info');
      }
    } catch (err) {
      console.error(err);
      showToast('Webhook simulation failed. Check backend console.', 'error');
    } finally {
      simulateWebhookBtn.disabled = false;
      simulateWebhookBtn.innerText = "Simulate Webhook";
    }
  });
}

/* Dashboard Renderer with Cascading Fallback Column */
function renderDashboard(records, prependOnly = false) {
  let totalLoss = 0;
  let recoverable = 0;
  let tripped = 0;

  const tbody = document.querySelector('#resultsTable tbody');
  const logBox = document.getElementById('telemetryLog');
  if (!tbody || !logBox) return;

  tbody.innerHTML = '';
  logBox.innerHTML = '';

  const recCount = document.getElementById('tableRecordCount');
  if (recCount) recCount.innerText = `${records.length} Records Ingested`;
  const failTag = document.getElementById('failureCountTag');
  if (failTag) failTag.innerText = `${records.length} Failed Txns`;

  records.forEach((rec, idx) => {
    totalLoss += rec.original_amount;
    if (!rec.stopping_rule_applied) recoverable += rec.original_amount;
    if (rec.stopping_rule_applied) tripped += 1;

    let badgeClass = 'badge-whatsapp';
    if (rec.action === 'SMART_RETRY') badgeClass = 'badge-retry';
    if (rec.action === 'HARD_STOP') badgeClass = 'badge-stop';
    if (rec.action === 'ALTERNATIVE_UPI_NUDGE') badgeClass = 'badge-nudge';

    const fallbackRoute = rec.action === 'SMART_RETRY'
      ? ((rec.payment_method || '').toLowerCase() === 'upi' ? 'NPCI Direct' : 'IMPS Rail')
      : (rec.action === 'ALTERNATIVE_UPI_NUDGE' ? 'UPI AutoPay' : 'Primary');

    const row = document.createElement('tr');
    row.setAttribute('tabindex', '0');
    row.innerHTML = `
      <td>
        <span class="cell-txnid">
          ${rec.transaction_id}
          <button class="copy-btn" data-copy="${rec.transaction_id}" aria-label="Copy Txn ID">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          </button>
        </span>
      </td>
      <td class="cell-customer">${rec.customer_name}</td>
      <td class="cell-amount">₹${rec.original_amount.toFixed(2)}</td>
      <td class="cell-category">${rec.category}</td>
      <td><span class="badge ${badgeClass}">${rec.action}</span></td>
      <td><span class="badge-fallback">${fallbackRoute}</span></td>
      <td class="cell-confidence">${(rec.confidence_score * 100).toFixed(0)}%</td>
    `;

    row.addEventListener('click', (e) => {
      if (e.target.closest('.copy-btn')) return;
      openHitlModal(rec, idx);
    });

    const cBtn = row.querySelector('.copy-btn');
    if (cBtn) {
      cBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        copyToClipboard(rec.transaction_id, cBtn);
      });
    }
    tbody.appendChild(row);

    const trace = document.createElement('div');
    trace.className = `trace-block ${rec.stopping_rule_applied ? 'stopped' : ''}`;
    trace.innerHTML = `
      <div class="trace-title">[${rec.transaction_id}] ${rec.action} &rarr; ${rec.category}</div>
      <div class="trace-audit">&bull; ${rec.audit_trace}</div>
      ${rec.customer_message ? `<div class="trace-nudge">💬 &quot;${rec.customer_message}&quot;</div>` : ''}
    `;
    logBox.appendChild(trace);
  });

  const tlEl = document.getElementById('totalLoss');
  if (tlEl) tlEl.innerText = `₹${totalLoss.toLocaleString('en-IN')}`;
  const rcEl = document.getElementById('recoveredAmount');
  if (rcEl) rcEl.innerText = `₹${recoverable.toLocaleString('en-IN')}`;
  const trEl = document.getElementById('trippedCount');
  if (trEl) trEl.innerText = tripped;

  const pct = totalLoss > 0 ? ((recoverable / totalLoss) * 100).toFixed(1) : 0;
  const rrTag = document.getElementById('recoveryRateTag');
  if (rrTag) rrTag.innerText = `${pct}% Retained`;
}

/* Analytics Updater */
function updateAnalytics(records) {
  const total = records.length;
  const stopped = records.filter(r => r.stopping_rule_applied).length;
  const dispatched = total - stopped;

  const fTotal = document.getElementById('funnelTotal');
  if (fTotal) fTotal.innerText = `${total} Events`;
  const fClassified = document.getElementById('funnelClassified');
  if (fClassified) fClassified.innerText = `${total} Validated`;
  const fDispatched = document.getElementById('funnelDispatched');
  if (fDispatched) fDispatched.innerText = `${dispatched} Recoveries`;
  const fStopped = document.getElementById('funnelStopped');
  if (fStopped) fStopped.innerText = `${stopped} Hard Stops`;

  const bar1 = document.getElementById('bar1');
  const bar2 = document.getElementById('bar2');
  const bar3 = document.getElementById('bar3');
  const bar4 = document.getElementById('bar4');

  if (total > 0) {
    if (bar1) bar1.style.width = '100%';
    if (bar2) bar2.style.width = '100%';
    if (bar3) bar3.style.width = `${(dispatched / total) * 100}%`;
    if (bar4) bar4.style.width = `${Math.max(5, (stopped / total) * 100)}%`;
  } else {
    if (bar1) bar1.style.width = '0%';
    if (bar2) bar2.style.width = '0%';
    if (bar3) bar3.style.width = '0%';
    if (bar4) bar4.style.width = '0%';
  }

  let upi = 0, mandate = 0, card = 0, netbanking = 0;
  records.forEach(r => {
    const m = (r.payment_method || '').toLowerCase();
    if (m === 'upi') upi++;
    else if (m === 'mandate') mandate++;
    else if (m === 'card') card++;
    else if (m === 'netbanking') netbanking++;
  });

  const upiEl = document.getElementById('upiCount');
  if (upiEl) upiEl.innerText = `${upi} Failures`;
  const mandateEl = document.getElementById('mandateCount');
  if (mandateEl) mandateEl.innerText = `${mandate} Failures`;
  const cardEl = document.getElementById('cardCount');
  if (cardEl) cardEl.innerText = `${card} Failures`;
  const netbankingEl = document.getElementById('netbankingCount');
  if (netbankingEl) netbankingEl.innerText = `${netbanking} Failures`;

  const totalEl = document.getElementById('railDonutTotal');
  if (totalEl) totalEl.innerText = total;

  const donut = document.getElementById('railDonut');
  if (donut) {
    if (total === 0) {
      donut.style.background = 'conic-gradient(var(--surface-3) 0deg 360deg)';
    } else {
      const uDeg = (upi / total) * 360;
      const mDeg = uDeg + (mandate / total) * 360;
      const cDeg = mDeg + (card / total) * 360;
      donut.style.background = `conic-gradient(var(--sky) 0deg ${uDeg}deg, var(--violet) ${uDeg}deg ${mDeg}deg, var(--amber) ${mDeg}deg ${cDeg}deg, var(--emerald) ${cDeg}deg 360deg)`;
    }
  }
}

/* Quarantine Vault & DLQ */
async function fetchDlqRecords() {
  const statusEl = document.getElementById('vaultStatus');
  try {
    const res = await fetch(`${API_BASE}/api/dlq-records`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    renderVault(data.records || []);
    if (statusEl) statusEl.innerText = 'SYNCED';
  } catch (err) {
    if (statusEl) statusEl.innerText = 'IDLE';
  }
}

function renderVault(records) {
  const listEl = document.getElementById('vaultList');
  const countEl = document.getElementById('vaultRecordCount');
  const vaultCount = document.getElementById('vaultCount');
  const vaultAmount = document.getElementById('vaultAmount');
  const vaultTabCount = document.getElementById('vaultTabCount');
  if (!listEl) return;

  if (countEl) countEl.innerText = `${records.length} Records`;
  if (vaultCount) vaultCount.innerText = records.length;
  if (vaultTabCount) vaultTabCount.innerText = `(${records.length})`;

  const total = records.reduce((s, r) => s + (r.amount || 0), 0);
  if (vaultAmount) vaultAmount.innerText = `₹${total.toLocaleString('en-IN')}`;

  if (records.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/></svg>
        <span class="empty-title">Vault is empty</span>
        <p>Transactions exceeding maximum retry ceilings route here automatically.</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = '';
  records.forEach(r => {
    const it = document.createElement('div');
    it.className = 'vault-item';
    it.innerHTML = `
      <span class="vault-txn">${r.transaction_id}</span>
      <span class="vault-customer">${r.customer_name}</span>
      <span class="vault-amount">₹${Number(r.amount).toFixed(2)}</span>
      <span class="vault-reason">${r.quarantine_reason || 'Exceeded maximum automated retry ceiling (3). Enforced anti-harassment stopping rule.'}</span>
      <button class="btn-pardon" data-id="${r.transaction_id}" data-name="${r.customer_name}" data-amount="₹${Number(r.amount).toFixed(2)}">Pardon &amp; Dispatch</button>
    `;

    const pardonBtn = it.querySelector('.btn-pardon');
    pardonBtn.addEventListener('click', () => {
      openPardonModal({
        id: r.transaction_id,
        name: r.customer_name,
        amount: `₹${Number(r.amount).toFixed(2)}`
      });
    });

    listEl.appendChild(it);
  });
}

const refreshBtn = document.getElementById('refreshVaultBtn');
if (refreshBtn) refreshBtn.addEventListener('click', fetchDlqRecords);

/* HITL Inspector Modal */
function openHitlModal(record, index) {
  selectedRecord = { record, index };
  document.getElementById('modalTxnId').innerText = record.transaction_id;
  document.getElementById('modalCustomerName').innerText = record.customer_name;
  document.getElementById('modalCustomerPhone').innerText = record.customer_phone || '+91 98765 43210';
  document.getElementById('modalCategory').innerText = record.category;
  document.getElementById('modalMethod').innerText = (record.payment_method || 'UPI').toUpperCase();
  document.getElementById('modalRawError').innerText = `[${record.raw_error_code || 'ERR_NPCI_TIMEOUT'}] ${record.raw_error_description || 'Switch timeout'}`;
  document.getElementById('modalAiCopy').value = record.customer_message || 'Silent retry cooling applied under anti-harassment policy.';

  const modal = document.getElementById('hitlModal');
  if (modal) modal.classList.add('open');
}

function closeHitlModal() {
  const modal = document.getElementById('hitlModal');
  if (modal) modal.classList.remove('open');
  selectedRecord = null;
}

const closeModalBtn = document.getElementById('closeModalBtn');
if (closeModalBtn) closeModalBtn.addEventListener('click', closeHitlModal);
const cancelModalBtn = document.getElementById('cancelModalBtn');
if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeHitlModal);

const approveBtn = document.getElementById('approveDispatchBtn');
if (approveBtn) {
  approveBtn.addEventListener('click', async () => {
    if (!selectedRecord) return;
    const newMsg = document.getElementById('modalAiCopy').value;
    try {
      await fetch(`${API_BASE}/api/hitl-override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction_id: selectedRecord.record.transaction_id, modified_message: newMsg })
      });
      currentRecords[selectedRecord.index].customer_message = newMsg;
      renderDashboard(currentRecords);
      showToast('Dunning copy approved.', 'success');
      closeHitlModal();
    } catch (e) {
      showToast('Override dispatch failed.', 'error');
    }
  });
}

/* DLQ Pardon Modal Handlers */
function openPardonModal(item) {
  activePardonTxn = item;
  document.getElementById('pardonTxnIdDisplay').innerText = item.id;
  document.getElementById('pardonCustomerName').innerText = item.name;
  document.getElementById('pardonAmount').innerText = item.amount;
  document.getElementById('pardonReasonInput').value = "Customer confirmed active balance via support; authorized manual 1-click recovery link.";
  document.getElementById('pardonModal').classList.add('open');
}

function closePardonModal() {
  document.getElementById('pardonModal').classList.remove('open');
  activePardonTxn = null;
}

const closePardonBtn = document.getElementById('closePardonModalBtn');
if (closePardonBtn) closePardonBtn.addEventListener('click', closePardonModal);

const cancelPardonBtn = document.getElementById('cancelPardonBtn');
if (cancelPardonBtn) cancelPardonBtn.addEventListener('click', closePardonModal);

const confirmPardonBtn = document.getElementById('confirmPardonBtn');
if (confirmPardonBtn) {
  confirmPardonBtn.addEventListener('click', async () => {
    if (!activePardonTxn) return;
    const reason = document.getElementById('pardonReasonInput').value;
    confirmPardonBtn.disabled = true;
    confirmPardonBtn.innerText = "Authorizing...";

    try {
      const res = await fetch(`${API_BASE}/api/dlq/pardon`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: activePardonTxn.id,
          reason: reason,
          officer_id: "RISK_OFFICER_03"
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      showToast(`Pardon Authorized: Link dispatched for ${activePardonTxn.id}`, 'success');
      appendLogEntry(`> [MANUAL PARDON]: ${activePardonTxn.id} pardoned by officer. Reason: "${reason}"`, 'system');

      closePardonModal();
      fetchDlqRecords();
      fetchComplianceHealth();
    } catch (err) {
      showToast('Failed to authorize pardon.', 'error');
    } finally {
      confirmPardonBtn.disabled = false;
      confirmPardonBtn.innerText = "Authorize & Force Dispatch";
    }
  });
}

function appendLogEntry(message, type) {
  const logBox = document.getElementById('telemetryLog');
  if (!logBox) return;
  const l = document.createElement('div');
  l.className = `terminal-line ${type}`;
  l.innerText = message;
  logBox.prepend(l);
}
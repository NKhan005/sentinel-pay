let currentRecords = [];
let chaosModeActive = false;
let selectedRecord = null;

// Tab View Navigation
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
    
    tab.classList.add('active');
    const targetView = tab.getAttribute('data-view');
    document.getElementById(`view-${targetView}`).classList.add('active');
  });
});

// Policy Sliders
document.getElementById('sliderMaxRetries').addEventListener('input', (e) => {
  document.getElementById('valMaxRetries').innerText = `${e.target.value} Attempts`;
});

document.getElementById('sliderBackoff').addEventListener('input', (e) => {
  document.getElementById('valBackoff').innerText = `${e.target.value} Minutes`;
});

// Direct Audit CSV Download Logging
const exportBtn = document.getElementById('exportCsvBtn');
if (exportBtn) {
  exportBtn.addEventListener('click', () => {
    appendLogEntry('> [AUDIT EXPORT]: RBI-compliant dunning trace downloaded successfully.', 'system');
  });
}

// Initialize Switches on Load
document.addEventListener('DOMContentLoaded', () => {
  fetchBankHealth();
});

async function fetchBankHealth() {
  try {
    const res = await fetch('http://localhost:8000/api/bank-switch-health');
    const switches = await res.json();
    const grid = document.getElementById('switchGrid');
    grid.innerHTML = '';

    switches.forEach(sw => {
      const node = document.createElement('div');
      const statusClass = sw.status.toLowerCase();
      node.className = `switch-node ${statusClass}`;
      node.innerHTML = `
        <div class="node-name">${sw.bank_name}</div>
        <div class="node-sub">
          <span>${sw.rail} &bull; ${sw.success_rate}% SR</span>
          <span>${sw.avg_latency_ms}ms</span>
        </div>
      `;
      grid.appendChild(node);
    });
  } catch (err) {
    console.warn("Could not sync bank switches.");
  }
}

// Chaos Mode Toggle
document.getElementById('chaosToggleBtn').addEventListener('click', () => {
  chaosModeActive = !chaosModeActive;
  const pill = document.getElementById('chaosToggleBtn');
  const label = pill.querySelector('.chaos-label');
  
  if (chaosModeActive) {
    pill.classList.add('active');
    label.innerHTML = 'Chaos: <strong>ACTIVE</strong>';
    appendLogEntry('> [CHAOS WARNING]: 429 Rate Limits & Network Jitter injection active.', 'system');
  } else {
    pill.classList.remove('active');
    label.innerHTML = 'Chaos: <strong>OFF</strong>';
    appendLogEntry('> [CHAOS RESTORED]: Standard production routes restored.', 'system');
  }
});

// Run 50-Record Batch
document.getElementById('runBatchBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runBatchBtn');
  const statusEl = document.getElementById('engineStatus');
  
  btn.disabled = true;
  btn.innerText = "Processing...";
  statusEl.innerText = "STREAMING";
  statusEl.style.color = "var(--amber)";

  try {
    const res = await fetch('http://localhost:8000/api/run-batch', { method: 'POST' });
    const data = await res.json();
    currentRecords = data;
    renderDashboard(currentRecords);
    updateAnalytics(currentRecords);
    statusEl.innerText = "ACTIVE";
    statusEl.style.color = "var(--emerald)";
  } catch (err) {
    alert("Backend connection error. Ensure FastAPI server is running on http://localhost:8000");
    statusEl.innerText = "ERR_OFFLINE";
    statusEl.style.color = "var(--ruby)";
  } finally {
    btn.disabled = false;
    btn.innerText = "Run Batch";
  }
});

// Webhook Simulation
document.getElementById('simulateWebhookBtn').addEventListener('click', async () => {
  const btn = document.getElementById('simulateWebhookBtn');
  btn.disabled = true;
  btn.innerText = "Ingesting...";

  const randomTxnNum = Math.floor(1000 + Math.random() * 9000);
  const mockWebhookPayload = {
    event: "payment.failed",
    payload: {
      payment: {
        entity: {
          id: `pay_live_${randomTxnNum}`,
          amount: 349900,
          method: "upi",
          error_code: chaosModeActive ? "GATEWAY_TIMEOUT_429" : "ISSUER_BANK_TIMEOUT",
          error_description: chaosModeActive ? "Chaos injection rate limit 429 simulated" : "NPCI switch timeout",
          contact: "+919876543210",
          notes: {
            customer_name: "Sneha Kulkarni",
            retry_count: chaosModeActive ? 3 : 0
          }
        }
      }
    }
  };

  try {
    const res = await fetch('http://localhost:8000/api/webhook/razorpay', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': 'mock_test_signature'
      },
      body: JSON.stringify(mockWebhookPayload)
    });
    const response = await res.json();
    
    if (response.decision) {
      currentRecords.unshift(response.decision);
      renderDashboard(currentRecords);
      updateAnalytics(currentRecords);
    }
  } catch (err) {
    alert("Error sending simulated webhook event.");
  } finally {
    btn.disabled = false;
    btn.innerText = "Simulate Webhook";
  }
});

function renderDashboard(records) {
  let totalLoss = 0;
  let recoverable = 0;
  let tripped = 0;

  const tbody = document.querySelector('#resultsTable tbody');
  const logBox = document.getElementById('telemetryLog');
  tbody.innerHTML = '';
  logBox.innerHTML = '';

  document.getElementById('tableRecordCount').innerText = `${records.length} Records Ingested`;
  document.getElementById('failureCountTag').innerText = `${records.length} Failed Txns`;

  records.forEach((rec, idx) => {
    totalLoss += rec.original_amount;
    if (!rec.stopping_rule_applied) recoverable += rec.original_amount;
    if (rec.stopping_rule_applied) tripped += 1;

    let badgeClass = 'badge-whatsapp';
    if (rec.action === 'SMART_RETRY') badgeClass = 'badge-retry';
    if (rec.action === 'HARD_STOP') badgeClass = 'badge-stop';
    if (rec.action === 'ALTERNATIVE_UPI_NUDGE') badgeClass = 'badge-nudge';

    const row = document.createElement('tr');
    row.innerHTML = `
      <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted);">${rec.transaction_id}</td>
      <td style="font-weight: 500;">${rec.customer_name}</td>
      <td style="font-family: 'JetBrains Mono', monospace; font-feature-settings: 'tnum';">₹${rec.original_amount.toFixed(2)}</td>
      <td style="font-size: 11px; color: var(--text-muted);">${rec.category}</td>
      <td><span class="badge ${badgeClass}">${rec.action}</span></td>
      <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--amber);">${(rec.confidence_score * 100).toFixed(0)}%</td>
    `;
    
    row.addEventListener('click', () => openHitlModal(rec, idx));
    tbody.appendChild(row);

    const traceBlock = document.createElement('div');
    traceBlock.className = `trace-block ${rec.stopping_rule_applied ? 'stopped' : ''}`;
    traceBlock.innerHTML = `
      <div class="trace-title">
        [${rec.transaction_id}] ${rec.action} &rarr; ${rec.category}
      </div>
      <div class="trace-audit">&bull; ${rec.audit_trace}</div>
      ${rec.customer_message ? `<div class="trace-nudge">💬 &quot;${rec.customer_message}&quot;</div>` : ''}
    `;
    logBox.appendChild(traceBlock);
  });

  document.getElementById('totalLoss').innerText = `₹${totalLoss.toLocaleString('en-IN')}`;
  document.getElementById('recoveredAmount').innerText = `₹${recoverable.toLocaleString('en-IN')}`;
  document.getElementById('trippedCount').innerText = tripped;
  
  const recoveryPct = totalLoss > 0 ? ((recoverable / totalLoss) * 100).toFixed(1) : 0;
  document.getElementById('recoveryRateTag').innerText = `${recoveryPct}% Retained`;
}

function updateAnalytics(records) {
  const total = records.length;
  const stopped = records.filter(r => r.stopping_rule_applied).length;
  const dispatched = total - stopped;

  document.getElementById('funnelTotal').innerText = `${total} Events`;
  document.getElementById('funnelClassified').innerText = `${total} Validated`;
  document.getElementById('funnelDispatched').innerText = `${dispatched} Recoveries`;
  document.getElementById('funnelStopped').innerText = `${stopped} Hard Stops`;

  if (total > 0) {
    document.getElementById('bar3').style.width = `${(dispatched / total) * 100}%`;
    document.getElementById('bar4').style.width = `${(stopped / total) * 100}%`;
  }

  // Multi-rail aggregation
  let upi = 0, mandate = 0, card = 0, netbanking = 0;
  records.forEach(r => {
    const m = (r.payment_method || '').toLowerCase();
    if (m === 'upi') upi++;
    else if (m === 'mandate') mandate++;
    else if (m === 'card') card++;
    else if (m === 'netbanking') netbanking++;
  });

  document.getElementById('upiCount').innerText = `${upi} Failures`;
  document.getElementById('mandateCount').innerText = `${mandate} Failures`;
  document.getElementById('cardCount').innerText = `${card} Failures`;
  document.getElementById('netbankingCount').innerText = `${netbanking} Failures`;
}

function openHitlModal(record, index) {
  selectedRecord = { record, index };
  document.getElementById('modalTxnId').innerText = record.transaction_id;
  document.getElementById('modalCustomerName').innerText = record.customer_name;
  document.getElementById('modalCustomerPhone').innerText = record.customer_phone || '+91 98765 43210';
  document.getElementById('modalCategory').innerText = record.category;
  document.getElementById('modalMethod').innerText = (record.payment_method || 'UPI').toUpperCase();
  document.getElementById('modalRawError').innerText = `[${record.raw_error_code || 'ERR_REASON'}] ${record.raw_error_description || 'Switch timeout'}`;
  document.getElementById('modalAiCopy').value = record.customer_message || 'No proactive nudge dispatched (Silent retry window active).';

  document.getElementById('hitlModal').classList.add('open');
}

function closeHitlModal() {
  document.getElementById('hitlModal').classList.remove('open');
  selectedRecord = null;
}

document.getElementById('closeModalBtn').addEventListener('click', closeHitlModal);
document.getElementById('cancelModalBtn').addEventListener('click', closeHitlModal);

document.getElementById('approveDispatchBtn').addEventListener('click', async () => {
  if (!selectedRecord) return;
  const newMsg = document.getElementById('modalAiCopy').value;

  try {
    await fetch('http://localhost:8000/api/hitl-override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transaction_id: selectedRecord.record.transaction_id,
        modified_message: newMsg
      })
    });

    currentRecords[selectedRecord.index].customer_message = newMsg;
    renderDashboard(currentRecords);
    appendLogEntry(`> [HITL OVERRIDE]: Transaction ${selectedRecord.record.transaction_id} message updated by merchant.`, 'system');
    closeHitlModal();
  } catch (err) {
    alert("Error sending override approval to backend.");
  }
});

function appendLogEntry(message, type) {
  const logBox = document.getElementById('telemetryLog');
  const line = document.createElement('div');
  line.className = `terminal-line ${type}`;
  line.innerText = message;
  logBox.prepend(line);
}
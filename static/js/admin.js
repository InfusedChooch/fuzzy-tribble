let passTimers = {};

/* ----------------------------------------------------------
   Load / refresh the active-pass table
---------------------------------------------------------- */
function loadPasses() {
  const tbody = document.getElementById('passes-table');
  tbody.innerHTML = '';
  passTimers = {};

  fetch('/admin_passes')
    .then(res => res.json())
    .then(data => {
      data.forEach(p => {
        const row = tbody.insertRow();
        row.className = p.status;

        const actionHtml = (p.status === 'pending_start')
          ? `<button onclick="approve(${p.id})">Approve</button>
             <button onclick="reject(${p.id})">Reject</button>`
          : `<button onclick="manualCheckIn(${p.id})">End Pass</button>`;

        const lastTag = p.last_event === 'in'
          ? '📍 In'
          : p.last_event === 'out'
          ? '➡️ Out'
          : '—';

        row.innerHTML = `
          <td>${p.id}</td>
          <td>${p.student_name}</td>
          <td>${p.room}</td>
          <td>${p.checkout || '—'}</td>
          <td>${p.station_out || '—'}</td>
          <td>${p.station_in || '—'}</td>
          <td>${lastTag}</td>
          <td id="timer-${p.id}">${p.elapsed || '—'}</td>
          <td>
            <input type="text" id="note-${p.id}" value="${p.note || ''}" placeholder="Add note">
            <button onclick="addNote('${p.student_id}', '${p.id}')">Save</button>
          </td>
          <td>${p.is_override ? '✔️' : ''}</td>
          <td>${actionHtml}</td>
        `;

        if (p.status === 'active' && p.checkout) {
          const parts = p.checkout.split(':').map(Number);
          passTimers[p.id] = parts;
        }
      });
    });
}

/* ----------------------------------------------------------
   Timer tick
---------------------------------------------------------- */
function updateTimers() {
  const now = new Date();
  Object.entries(passTimers).forEach(([passId, parts]) => {
    const t0 = new Date();
    t0.setHours(parts[0], parts[1], parts[2], 0);
    let diff = Math.floor((now - t0) / 1000);
    diff = Math.max(diff, 0);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const cell = document.getElementById(`timer-${passId}`);
    if (cell) cell.textContent = `${minutes}m ${seconds}s`;
  });
}

/* ----------------------------------------------------------
   Admin actions
---------------------------------------------------------- */
function manualCheckIn(passId) {
  fetch(`/admin_checkin/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      loadPasses();
    });
}

function approve(passId) {
  fetch(`/admin/approve/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      loadPasses();
    });
}

function reject(passId) {
  fetch(`/admin/reject/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      loadPasses();
    });
}

function addNote(studentId, passId) {
  const note = document.getElementById(`note-${passId}`).value;
  fetch(`/admin_add_note/${studentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note })
  })
    .then(res => res.json())
    .then(data => { alert(data.message); });
}

/* ----------------------------------------------------------
   Create override pass
---------------------------------------------------------- */
document.getElementById('create-pass-form')?.addEventListener('submit', function (e) {
  e.preventDefault();
  const studentId = document.getElementById('student_id').value.trim();
  fetch('/admin_create_pass', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id: studentId })
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      loadPasses();
      this.reset();
    });
});

/* ----------------------------------------------------------
   Change admin password
---------------------------------------------------------- */
document.getElementById('change-password-form')?.addEventListener('submit', function (e) {
  e.preventDefault();
  const currentPass = document.getElementById('current_pass').value;
  const newPass = document.getElementById('new_pass').value;
  const confirmPass = document.getElementById('confirm_pass').value;

  fetch('/admin_change_password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPass,
      new_password: newPass,
      confirm_password: confirmPass
    })
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById('password-msg').textContent = data.message;
      if (data.success) this.reset();
    });
});

/* ----------------------------------------------------------
   Smart refresh on pending changes
---------------------------------------------------------- */
let previousPendingCount = 0;

function checkForPendingChanges() {
  fetch('/admin_pending_count')
    .then(res => res.json())
    .then(data => {
      const total = data.pending_start + data.pending_return;
      if (total > previousPendingCount) {
        alert("New pending request(s).");
      }
      previousPendingCount = total;
    });
}

/* ----------------------------------------------------------
   Kickoff
---------------------------------------------------------- */
setInterval(updateTimers, 1000);
setInterval(loadPasses, 5000);
setInterval(checkForPendingChanges, 10000);
loadPasses();

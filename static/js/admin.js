let passTimers = {};

/* ----------------------------------------------------------
   Load / refresh the active‑pass table
---------------------------------------------------------- */
function loadPasses() {
  const savedNotes = {};
  document.querySelectorAll('[id^=note-]').forEach(inp => {
    savedNotes[inp.id] = inp.value;
  });

  fetch('/admin_passes')
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector('#passes-table tbody');
      tbody.innerHTML = '';
      passTimers = {};

      data.forEach(p => {
        const row = tbody.insertRow();
        const isPending = (p.status === 'pending');

        const actionHtml = isPending
          ? `<button onclick="approve(${p.pass_id})">Approve</button>
             <button onclick="reject(${p.pass_id})">Reject</button>`
          : `<button onclick="manualCheckIn(${p.pass_id})">End&nbsp;Pass</button>`;

        row.className = isPending ? 'pending-row' : '';

        row.innerHTML = `
          <td>${p.pass_id}</td>
          <td>${p.student_id}</td>
          <td>${p.student_name}</td>
          <td>${p.room_time}</td>
          <td>${p.station_in}</td>
          <td>${p.station_out}</td>
          <td id="timer-${p.pass_id}">${isPending ? '—' : p.elapsed}</td>
          <td>
            <input type="text" id="note-${p.pass_id}"
                   value="${savedNotes[`note-${p.pass_id}`] || p.note || ''}"
                   placeholder="Add note">
            <button onclick="addNote('${p.student_id}', '${p.pass_id}')">Save</button>
          </td>
          <td>${p.is_override ? '✔️' : ''}</td>
          <td>${actionHtml}</td>
        `;

        // For stopwatch
        if (!isPending && p.room_time.includes('@')) {
          const rawTime = p.room_time.split('@')[1].trim();
          passTimers[p.pass_id] = rawTime;
        }
      });
    });
}

/* ----------------------------------------------------------
   Timer tick (updates each active row every second)
---------------------------------------------------------- */
function updateTimers() {
  const now = new Date();
  Object.entries(passTimers).forEach(([passId, timeOutStr]) => {
    if (!timeOutStr) return;
    const parts = timeOutStr.split(':').map(Number);
    const t0 = new Date();
    t0.setHours(parts[0], parts[1], parts[2], 0);

    let diff = Math.floor((now - t0) / 1000);
    diff = Math.max(diff, 0);

    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const timerEl = document.getElementById(`timer-${passId}`);
    if (timerEl) timerEl.textContent = `${minutes}m ${seconds}s`;
  });
}

/* ----------------------------------------------------------
   Admin actions
---------------------------------------------------------- */
function manualCheckIn(passId) {
  fetch(`/admin_checkin/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => { alert(data.message); loadPasses(); });
}

function approve(passId) {
  fetch(`/admin/approve/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => { alert(data.message); loadPasses(); });
}

function reject(passId) {
  fetch(`/admin/reject/${passId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => { alert(data.message); loadPasses(); });
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
   Override-pass creator
---------------------------------------------------------- */
document.getElementById('create-pass-form').addEventListener('submit', function (e) {
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
   Change‑password handler
---------------------------------------------------------- */
document.getElementById('change-password-form').addEventListener('submit', function (e) {
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
   Smart conditional refresh every 10s if new pending requests
---------------------------------------------------------- */
let previousPendingCount = 0;

function checkForPendingChanges() {
  fetch('/admin_pending_count')
    .then(res => res.json())
    .then(data => {
      const total = data.pending_start + data.pending_return;
      if (total > previousPendingCount) {
        window.location.reload();
      }
      previousPendingCount = total;
    });
}

// Check every 10 seconds
setInterval(checkForPendingChanges, 10000);
/* ----------------------------------------------------------
   Manual “Refresh All” nav link
---------------------------------------------------------- */
function manualRefresh() { loadPasses(); }

/* ----------------------------------------------------------
   Kick-off intervals
---------------------------------------------------------- */
setInterval(updateTimers, 1000);   // stopwatch
setInterval(loadPasses, 5000);     // table refresh
loadPasses();

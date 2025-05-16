// admin.js
let passTimers = {};

/* ----------------------------------------------------------
   Load / refresh the active-pass table
---------------------------------------------------------- */
function loadPasses() {
  const tbody = document.getElementById('passes-table');
  if (!tbody) return;

  // 📝 Preserve note input values before refresh
  const currentNotes = {};
  document.querySelectorAll('[id^="note-"]').forEach(input => {
    const passId = input.id.split('-')[1];
    currentNotes[passId] = input.value;
  });

  tbody.innerHTML = '';
  passTimers = {};

  fetch('/admin_passes')
    .then(res => res.json())
    .then(data => {
      data.forEach(p => {
        const row = tbody.insertRow();
        row.className = p.status;

        const actionHtml = p.status === 'pending_start'
          ? `<button onclick="approve(${p.pass_id})">Approve</button>
             <button onclick="reject(${p.pass_id})">Reject</button>`
          : `<button onclick="manualCheckIn(${p.pass_id})">End Pass</button>`;

        row.innerHTML = `
          <td>${p.pass_id}</td>
          <td>${p.student_name}</td>
          <td>${p.date || '—'}</td>
          <td>${p.period || '—'}</td>
          <td>${p.room_time || '—'}</td>
          <td>${p.station_in || '—'}</td>
          <td>${p.station_out || '—'}</td>
          <td>${p.room_in || '—'}</td>
          <td id="timer-${p.pass_id}">${p.elapsed || '—'}</td>
          <td>${p.hallway_time || '—'}</td>
          <td>${p.station_time || '—'}</td>
          <td>${actionHtml}</td>
          <td>
            <input type="text" id="note-${p.pass_id}" value="${p.note || ''}" placeholder="Add note">
            <button onclick="addNote('${p.student_id}', '${p.pass_id}')">Save</button>
          </td>
          <td>${p.is_override ? '✔️ Override' : ''}</td>
        `;

        // Restore notes
        const noteInput = document.getElementById(`note-${p.pass_id}`);
        if (noteInput && currentNotes[p.pass_id] !== undefined) {
          noteInput.value = currentNotes[p.pass_id];
        }

        if (p.status === 'active' && p.room_time && p.room_time.includes('@')) {
          const [, timePart] = p.room_time.split('@');
          const [h, m, s] = timePart.trim().split(':').map(Number);
          passTimers[p.pass_id] = [h, m, s];
        }
      });
    });
}

/* ----------------------------------------------------------
   Load / refresh pending-pass table
---------------------------------------------------------- */
function loadPendingPasses() {
  const tbody = document.getElementById('pending-table');
  if (!tbody) return;

  fetch('/admin_pending_passes')
    .then(res => res.json())
    .then(data => {
      tbody.innerHTML = '';
      data.forEach(p => {
        const row = tbody.insertRow();
        row.className = p.status;

        const actionCell = p.status === 'pending_start'
          ? `<button onclick="approve(${p.pass_id})">Approve</button>
             <button onclick="reject(${p.pass_id})">Reject</button>`
          : `<button onclick="manualCheckIn(${p.pass_id})">End Pass</button>`;

        row.innerHTML = `
          <td>${p.student_id}</td>
          <td>${p.student_name}</td>
          <td>${p.room}</td>
          <td>${p.time}</td>
          <td>${p.status === 'pending_start' ? 'Start' : 'Stop'}</td>
          <td>${actionCell}</td>
        `;
      });
    });
}

/* ----------------------------------------------------------
   Timer updates for station/room durations
---------------------------------------------------------- */
function updateTimers() {
  const now = new Date();
  Object.entries(passTimers).forEach(([passId, [h, m, s]]) => {
    const start = new Date();
    start.setHours(h, m, s, 0);
    let diff = Math.floor((now - start) / 1000);
    diff = Math.max(diff, 0);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const cell = document.getElementById(`timer-${passId}`);
    if (cell) cell.textContent = `${minutes}m ${seconds}s`;
  });
}

/* ----------------------------------------------------------
   Admin actions: approve, reject, manual check-in
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
    .then(data => {
      alert(data.message);
      loadPasses();
    });
}

/* ----------------------------------------------------------
   Create override pass
---------------------------------------------------------- */
document.getElementById('create-pass-form')?.addEventListener('submit', function (e) {
  e.preventDefault();
  const studentId = document.getElementById('student_id').value.trim();
  const roomOut = document.getElementById('override_room')?.value.trim();
  const period = document.getElementById('override_period')?.value.trim();

  const payload = { student_id: studentId };
  if (roomOut) payload.room = roomOut;
  if (period) payload.period = period;

  fetch('/admin_create_pass', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
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
    body: JSON.stringify({ current_password: currentPass, new_password: newPass, confirm_password: confirmPass })
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById('password-msg').textContent = data.message;
      if (data.success) this.reset();
    });
});

/* ----------------------------------------------------------
   Open popout station view
---------------------------------------------------------- */
function openStationView(event) {
  event.preventDefault();
  const station = document.getElementById('station-selector')?.value;
  if (station) {
    window.open(`/station_view/${station}`, '_blank', 'width=800,height=600');
  }
}

/* ----------------------------------------------------------
   Collapsible sections + toggle all
---------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  const toggleAllBtn = document.getElementById("toggle-all");
  const collapsibles = Array.from(document.querySelectorAll(".collapsible"));

  collapsibles.forEach((btn, idx) => {
    const key = `collapsible-${idx}`;
    const content = btn.nextElementSibling;
    const saved = localStorage.getItem(key);
    content.style.display = saved === "none" ? "none" : "block";

    btn.addEventListener("click", () => {
      const isOpen = content.style.display !== "none";
      content.style.display = isOpen ? "none" : "block";
      localStorage.setItem(key, isOpen ? "none" : "block");
    });
  });

  toggleAllBtn?.addEventListener("click", () => {
    const anyOpen = collapsibles.some(btn => btn.nextElementSibling.style.display !== "none");
    collapsibles.forEach((btn, idx) => {
      const key = `collapsible-${idx}`;
      const content = btn.nextElementSibling;
      const newState = anyOpen ? "none" : "block";
      content.style.display = newState;
      localStorage.setItem(key, newState);
    });
    toggleAllBtn.textContent = anyOpen ? "🔼 Expand All" : "🔽 Collapse All";
  });
});

/* ----------------------------------------------------------
   Kickoff interval updates
---------------------------------------------------------- */
setInterval(updateTimers, 1000);
setInterval(loadPasses, 5000);
setInterval(loadPendingPasses, 5000);
loadPendingPasses();
loadPasses();

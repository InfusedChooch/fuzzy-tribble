// admin.js
let passTimers = {};
const isTeacher = window.userRole === "teacher";


/* ----------------------------------------------------------
   Load / refresh the active-pass table
---------------------------------------------------------- */
function loadPasses() {
  const tbody = document.getElementById('passes-table');
  if (!tbody) return;

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

        const noteInput = document.getElementById(`note-${p.pass_id}`);
        if (noteInput && currentNotes[p.pass_id] !== undefined) {
          noteInput.value = currentNotes[p.pass_id];
        }

        if (p.status === 'active' && p.room_time?.includes('@')) {
          const [, timePart] = p.room_time.split('@');
          const [h, m, s] = timePart.trim().split(':').map(Number);
          passTimers[p.pass_id] = [h, m, s];
        }
      });
    });
}

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

function refreshStationList() {
  fetch('/admin_rooms')
    .then(res => res.json())
    .then(data => {
      const active = data.filter(r => r.active).map(r => r.room);
      const container = document.getElementById("station-list");
      if (!container) return;
      container.innerHTML = active.length === 0
        ? "📍 <strong>Open Stations:</strong> <em>None</em>"
        : `📍 <strong>Open Stations:</strong> ${
            active.map(r => `<code><a href="#" onclick="openWindowRemembered('/station_view/${r}', 'station-${r}')">${r}</a></code>`).join(", ")
          }`;
    })
    .catch(err => console.error("Failed to refresh station list:", err));
}

function openWindowRemembered(path, name) {
  const key = `windowSettings-${name}`;
  const settings = JSON.parse(localStorage.getItem(key) || '{}');
  const width = settings.width || 600;
  const height = settings.height || 700;
  const left = settings.left || (window.screenX + 100);
  const top = settings.top || (window.screenY + 100);

  const features = `width=${width},height=${height},left=${left},top=${top},scrollbars=yes`;
  const win = window.open(path, name, features);

  win.addEventListener('beforeunload', () => {
    try {
      const x = win.screenX, y = win.screenY;
      const w = win.outerWidth, h = win.outerHeight;
      localStorage.setItem(key, JSON.stringify({ left: x, top: y, width: w, height: h }));
    } catch (e) {
      console.warn("❌ Failed to save window size/position:", e);
    }
  });
}

function openPasswordPopup() {
  const popup = document.createElement('div');
  popup.style.position = 'fixed';
  popup.style.top = '25%';
  popup.style.left = '35%';
  popup.style.padding = '20px';
  popup.style.background = '#fff';
  popup.style.border = '2px solid #000';
  popup.style.zIndex = 9999;
  popup.style.boxShadow = '4px 4px 10px rgba(0,0,0,0.3)';
  popup.innerHTML = `
    <h3>Change Password</h3>
    <input type="password" id="curPass" placeholder="Current Password"><br><br>
    <input type="password" id="newPass" placeholder="New Password"><br><br>
    <input type="password" id="confPass" placeholder="Confirm New"><br><br>
    <button onclick="submitPasswordChange()">Submit</button>
    <button onclick="this.parentElement.remove()">Cancel</button>
    <p id="pw-msg" style="margin-top: 10px;"></p>
  `;
  document.body.appendChild(popup);
}

function submitPasswordChange() {
  const current_password = document.getElementById('curPass').value;
  const new_password = document.getElementById('newPass').value;
  const confirm_password = document.getElementById('confPass').value;

  fetch('/change_password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password, new_password, confirm_password })
  })
    .then(res => res.json())
    .then(data => {
      const msg = document.getElementById('pw-msg');
      msg.textContent = data.message;
      if (data.success) {
        setTimeout(() => {
          msg.closest('div').remove();  // ⛔ remove popup
          location.reload();
        }, 1000);
      }
    });
}

document.addEventListener('DOMContentLoaded', () => {
  const name = window.userName || "User";
  const greeting = new Date().getHours() < 12 ? "Good morning" : "Welcome";
  document.getElementById('welcome-msg').textContent = `${greeting}, ${name}`;

  const form = document.getElementById('create-pass-form');
  if (form && !isTeacher) {
    form.addEventListener('submit', function (e) {
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
  }

  refreshStationList();
  setInterval(refreshStationList, 5000);
  setInterval(updateTimers, 1000);
  setInterval(loadPasses, 5000);
  setInterval(loadPendingPasses, 5000);
  loadPasses();
  loadPendingPasses();
});

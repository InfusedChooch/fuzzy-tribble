// admin.js
let passTimers = {};
const isTeacher = window.userRole === "teacher";

/* ----------------------------------------------------------
   Section: Initialization
---------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  const name = window.userName || "User";
  const greeting = new Date().getHours() < 12 ? "Good morning" : "Welcome";
  document.getElementById('welcome-msg').textContent = `${greeting}, ${name}`;

  setupOverrideForm();
  refreshStationList();
  loadPasses();
  loadPendingPasses();

  setInterval(refreshStationList, 5000);
  setInterval(updateTimers, 1000);
  setInterval(loadPasses, 5000);
  setInterval(loadPendingPasses, 5000);

  if (window.needsScheduleSetup) openSchedulePopup();
});

/* ----------------------------------------------------------
   Section: Pass List Management
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
        row.innerHTML = generatePassRow(p);
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
        row.innerHTML = generatePendingRow(p);
      });
    });
}

function generatePassRow(p) {
  const actionHtml = p.status === 'pending_start'
    ? `<button onclick="approve(${p.pass_id})">Approve</button>
       <button onclick="reject(${p.pass_id})">Reject</button>`
    : `<button onclick="manualCheckIn(${p.pass_id})">End Pass</button>`;
  return `
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
}

function generatePendingRow(p) {
  const action = p.status === 'pending_start'
    ? `<button onclick="approve(${p.pass_id})">Approve</button>
       <button onclick="reject(${p.pass_id})">Reject</button>`
    : `<button onclick="manualCheckIn(${p.pass_id})">End Pass</button>`;
  return `
    <td>${p.student_id}</td>
    <td>${p.student_name}</td>
    <td>${p.room}</td>
    <td>${p.time}</td>
    <td>${p.status === 'pending_start' ? 'Start' : 'Stop'}</td>
    <td>${action}</td>
  `;
}

function updateTimers() {
  const now = new Date();
  for (const [passId, [h, m, s]] of Object.entries(passTimers)) {
    const start = new Date();
    start.setHours(h, m, s, 0);
    const diff = Math.max(Math.floor((now - start) / 1000), 0);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const cell = document.getElementById(`timer-${passId}`);
    if (cell) cell.textContent = `${minutes}m ${seconds}s`;
  }
}

/* ----------------------------------------------------------
   Section: Pass Actions
---------------------------------------------------------- */
function manualCheckIn(id) {
  fetch(`/admin_checkin/${id}`, { method: 'POST' })
    .then(res => res.json()).then(data => {
      alert(data.message);
      loadPasses();
    });
}
function approve(id) {
  fetch(`/admin/approve/${id}`, { method: 'POST' })
    .then(res => res.json()).then(data => {
      alert(data.message);
      loadPasses();
    });
}
function reject(id) {
  fetch(`/admin/reject/${id}`, { method: 'POST' })
    .then(res => res.json()).then(data => {
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
    .then(res => res.json()).then(data => {
      alert(data.message);
      loadPasses();
    });
}

/* ----------------------------------------------------------
   Section: Station & Override Tools
---------------------------------------------------------- */
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
    });
}

function setupOverrideForm() {
  const form = document.getElementById('create-pass-form');
  if (!form || isTeacher) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const studentId = document.getElementById('student_id').value.trim();
    const roomOut = document.getElementById('override_room')?.value.trim();
    const period = document.getElementById('override_period')?.value.trim();
    const payload = { student_id: studentId, room: roomOut, period };

    fetch('/admin_create_pass', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        alert(data.message);
        loadPasses();
        form.reset();
      });
  });
}

/* ----------------------------------------------------------
   Section: Popups (Password + Settings + Schedule)
---------------------------------------------------------- */
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
      const { screenX, screenY, outerWidth, outerHeight } = win;
      localStorage.setItem(key, JSON.stringify({
        left: screenX, top: screenY, width: outerWidth, height: outerHeight
      }));
    } catch (e) {}
  });
}

function openPasswordPopup() {
  const popup = document.createElement('div');
  popup.style.cssText = 'position:fixed;top:25%;left:35%;padding:20px;background:#fff;border:2px solid #000;z-index:9999;box-shadow:4px 4px 10px rgba(0,0,0,0.3)';
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
  const current = document.getElementById('curPass').value;
  const newPass = document.getElementById('newPass').value;
  const confirm = document.getElementById('confPass').value;

  fetch('/change_password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password: current, new_password: newPass, confirm_password: confirm })
  })
    .then(res => res.json())
    .then(data => {
      const msg = document.getElementById('pw-msg');
      msg.textContent = data.message;
      if (data.success) {
        setTimeout(() => popup.remove(), 1000);
      }
    });
}

  function openSchedulePopup(existing = {}) {
  const popup = document.createElement('div');
  popup.style.position = 'fixed';
  popup.style.top = '10%';
  popup.style.left = '50%';
  popup.style.transform = 'translateX(-50%)';
  popup.style.background = '#fff';
  popup.style.border = '2px solid #444';
  popup.style.padding = '20px';
  popup.style.zIndex = 9999;
  popup.style.boxShadow = '0 0 10px rgba(0,0,0,0.3)';
  popup.innerHTML = `<h3>Set Your Schedule</h3>`;

  const periods = [
    "period_0", "period_1", "period_2", "period_3", "period_4_5",
    "period_5_6", "period_6_7", "period_7_8", "period_9",
    "period_10", "period_11", "period_12"
  ];

  const form = document.createElement('form');
  form.style.maxHeight = '400px';
  form.style.overflowY = 'auto';

  periods.forEach(period => {
    const label = document.createElement('label');
    label.textContent = `${period}: `;
    label.style.display = 'block';
    const input = document.createElement('input');
    input.type = 'text';
    input.name = period;
    input.value = existing[period] || '';
    input.style.marginBottom = '8px';
    input.style.width = '100%';
    form.appendChild(label);
    form.appendChild(input);
  });

  const submitBtn = document.createElement('button');
  submitBtn.textContent = "Save";
  submitBtn.type = "submit";
  submitBtn.style.marginTop = '10px';

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = "Cancel";
  cancelBtn.type = "button";
  cancelBtn.onclick = () => popup.remove();
  cancelBtn.style.marginLeft = '10px';

  form.appendChild(submitBtn);
  form.appendChild(cancelBtn);
  popup.appendChild(form);
  document.body.appendChild(popup);

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    const data = {};
    new FormData(form).forEach((val, key) => {
      data[key] = val.trim();
    });

    fetch('/setup_schedule', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(d => {
      alert(d.message);
      popup.remove();
      location.reload(); // refresh visibility of rooms
    });
  });
}


function openSettingsPopup() {
  const popup = document.createElement('div');
  popup.style.cssText = 'position:fixed;top:20%;left:50%;transform:translateX(-50%);background:#fff;border:2px solid #000;padding:20px;z-index:9999;box-shadow:0 0 10px rgba(0,0,0,0.3)';
  popup.innerHTML = `
    <h3>⚙️ Settings</h3>
    <button onclick="openSchedulePopup()">🗂 Edit Schedule</button><br><br>
    <button onclick="openPasswordPopup()">🔑 Change Password</button><br><br>
    <button onclick="this.parentElement.remove()">❌ Close</button>
  `;
  document.body.appendChild(popup);
}

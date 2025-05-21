// index.js – Student landing logic only

/* ----------------------------------------------------------
   Render student-safe room dot view (read-only)
---------------------------------------------------------- */
function drawStudentRoomDots(data) {
  const container = document.getElementById('room-dot-container');
  if (!container) return;
  container.innerHTML = '';

  data.forEach(room => {
    const wrapper = document.createElement('div');
    wrapper.style.border = room.is_current ? '3px solid #2ecc71' : '1px solid #ccc';
    wrapper.style.borderRadius = '10px';
    wrapper.style.padding = '10px';
    wrapper.style.margin = '8px';
    wrapper.style.minWidth = '120px';
    wrapper.style.textAlign = 'center';
    wrapper.style.background = room.active ? '#fff' : '#f0f0f0';

    const title = document.createElement('div');
    title.textContent = room.room + (room.type === 'station' ? ' (Station)' : '');
    title.style.fontWeight = 'bold';
    title.style.marginBottom = '6px';
    wrapper.appendChild(title);

    const dotWrap = document.createElement('div');
    dotWrap.title = `${room.free} free of ${room.free + room.taken} total`;

    for (let i = 0; i < room.taken; i++) {
      const d = document.createElement('span');
      d.className = 'dot taken';
      dotWrap.appendChild(d);
    }
    for (let i = 0; i < room.pending; i++) {
      const d = document.createElement('span');
      d.className = 'dot pending';
      dotWrap.appendChild(d);
    }
    for (let i = 0; i < room.free; i++) {
      const d = document.createElement('span');
      d.className = 'dot free';
      dotWrap.appendChild(d);
    }

    wrapper.appendChild(dotWrap);

    if (room.is_current) {
      const badge = document.createElement('div');
      badge.textContent = "✅ Your Current Room";
      badge.style.marginTop = '8px';
      badge.style.fontSize = '0.9em';
      badge.style.color = 'green';
      badge.style.fontWeight = 'bold';
      wrapper.appendChild(badge);
    }

    container.appendChild(wrapper);
  });
}

/* ----------------------------------------------------------
   Fetch and display room slots
---------------------------------------------------------- */
function loadRoomDots() {
  fetch('/student_slot_view')
    .then(res => res.json())
    .then(drawStudentRoomDots)
    .catch(err => console.error("❌ Failed to load student slots:", err));
}

/* ----------------------------------------------------------
   Clock + Period sync
---------------------------------------------------------- */
function updateCustomClock() {
  const now = new Date();
  const weekday = now.toLocaleDateString(undefined, { weekday: 'long' });
  const date = now.toLocaleDateString(undefined, { month: 'long', day: 'numeric' });
  const time = now.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  const el = document.getElementById('custom-clock');
  if (el) el.textContent = `${weekday}, ${date} ${time}`;
}

function updatePeriod() {
  fetch('/debug_period')
    .then(res => res.json())
    .then(data => {
      const current = Array.isArray(data) ? data.find(p => p.match) : data;
      const el = document.getElementById('period');
      if (el) el.textContent = current ? `Current Period: ${current.period}` : 'Outside scheduled periods';
    });
}

/* ----------------------------------------------------------
   Password popup
---------------------------------------------------------- */
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
          msg.closest('div').remove();
          location.reload();
        }, 1000);
      }
    });
}

/* ----------------------------------------------------------
   Init
---------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  const name = window.userName || "User";
  const greeting = new Date().getHours() < 12 ? "Good morning" : "Welcome";
  const welcome = document.getElementById('welcome-msg');
  if (welcome) welcome.textContent = `${greeting}, ${name}`;

  updateCustomClock();
  updatePeriod();
  loadRoomDots();

  setInterval(updateCustomClock, 1000);
  setInterval(updatePeriod, 30000);
  setInterval(loadRoomDots, 5000);
});

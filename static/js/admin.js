let passTimers = {};

function loadPasses() {
  const savedNotes = {};
  document.querySelectorAll('[id^=note-]').forEach(input => {
    savedNotes[input.id] = input.value;
  });

  fetch('/admin_passes')
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector('#passes-table tbody');
      tbody.innerHTML = '';
      passTimers = {};

      data.forEach(p => {
        const row = tbody.insertRow();
        row.innerHTML = `
          <td>${p.pass_id}</td>
          <td>${p.student_id}</td>
          <td>${p.student_name}</td>
          <td>${p.time_out}</td>
          <td id="timer-${p.pass_id}">0s</td>
          <td>
            <input type="text" id="note-${p.pass_id}" value="${savedNotes[`note-${p.pass_id}`] || ''}" placeholder="Add note">
            <button onclick="addNote('${p.student_id}', '${p.pass_id}')">Save</button>
          </td>
          <td>${p.is_override ? '✔️' : ''}</td>
          <td><button onclick="manualCheckIn(${p.pass_id})">End Pass</button></td>
        `;
        passTimers[p.pass_id] = p.time_out;
      });
    });
}

function updateTimers() {
  const now = new Date();
  Object.entries(passTimers).forEach(([passId, timeOutStr]) => {
    const parts = timeOutStr.split(':').map(Number);
    const timeOutDate = new Date();
    timeOutDate.setHours(parts[0], parts[1], parts[2], 0);
    let diff = Math.floor((now - timeOutDate) / 1000);
    diff = Math.max(diff, 0);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const display = `${minutes}m ${seconds}s`;
    const timerElem = document.getElementById(`timer-${passId}`);
    if (timerElem) timerElem.textContent = display;
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
  });
}

document.getElementById('create-pass-form').addEventListener('submit', function(e) {
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

document.getElementById('change-password-form').addEventListener('submit', function(e) {
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

function manualRefresh() {
  loadPasses();
}

setInterval(updateTimers, 1000);
setInterval(loadPasses, 5000);
loadPasses();

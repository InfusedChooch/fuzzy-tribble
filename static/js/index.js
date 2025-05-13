function updateClock() {
  const now = new Date();
  let h = now.getHours(),
      m = now.getMinutes(),
      s = now.getSeconds();
  const ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  document.getElementById('clock').textContent =
    `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')} ${ampm}`;
}

function refreshPasses() {
  fetch('/passes')
    .then(res => res.json())
    .then(slots => {
      const container = document.getElementById('pass-container');
      container.innerHTML = '';
      slots.forEach((slot, i) => {
        const box = document.createElement('div');
        box.className = `pass-box ${slot.status}`;

        const symbol = slot.status === 'free' ? '🟢 O'
                      : slot.status === 'pending_start' ? '🔵 ■'
                      : '🔴 ✕';

        const text = slot.status === 'free' ? 'Open'
                    : slot.status === 'pending_start' ? 'Pending'
                    : `${slot.student_name}`;

        box.innerHTML = `
          <div class="symbol">${symbol}</div>
          <div class="status-text">${text}</div>
          <div class="id-label">Slot ${i + 1}</div>
          <div class="room-label">${slot.room ? 'Room ' + slot.room : ''}</div>
        `;
        container.appendChild(box);
      });
    });
}

document.getElementById('check-form')?.addEventListener('submit', function(e) {
  e.preventDefault();
  const formData = new FormData(this);
  fetch('/request_pass', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById('message').textContent = data.message;
    refreshPasses();
    this.reset();
  });
});

setInterval(updateClock, 1000);
setInterval(refreshPasses, 5000);
updateClock();
refreshPasses();

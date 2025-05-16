// index.js
/* ----------------------------------------------------------
   Refresh pass display
---------------------------------------------------------- */
function refreshPasses() {
  fetch('/passes')
    .then(res => res.json())
    .then(slots => {
      const container = document.getElementById('pass-container');
      if (!container) return;
      container.innerHTML = '';
      slots.forEach((slot, i) => {
        const box = document.createElement('div');
        box.className = `pass-box ${slot.status}`;
        const symbol = slot.status === 'free' ? '🟢 O'
                      : slot.status === 'pending_start' ? '🔵 ■'
                      : '🔴 ✕';
        const text = slot.status === 'free' ? 'Open'
                    : slot.status === 'pending_start' ? 'Pending'
                    : slot.student_name;
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

/* ----------------------------------------------------------
   Handle pass request form
---------------------------------------------------------- */
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

/* ----------------------------------------------------------
   Custom clock and period updater
---------------------------------------------------------- */
export function updateCustomClock() {
  const now = new Date();
  const weekday = now.toLocaleDateString(undefined, { weekday: 'long' });
  const date = now.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
  const time = now.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  const el = document.getElementById('custom-clock');
  if (el) el.textContent = `${weekday}, ${date} ${time.toLowerCase()}`;
}

export function updatePeriod() {
  fetch('/debug_period')
    .then(res => res.json())
    .then(data => {
      let current = null;
      if (Array.isArray(data)) current = data.find(p => p.match);
      else if (data.match) current = data;
      const periodEl = document.getElementById('period');
      if (periodEl) {
        periodEl.textContent = current
          ? `Current Period: ${current.period}`
          : 'Outside scheduled periods';
      }
    });
}

/* ----------------------------------------------------------
   Init on DOM ready
---------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  refreshPasses();
  updateCustomClock();
  updatePeriod();
  setInterval(updateCustomClock, 1000);
  setInterval(updatePeriod, 30000);
});

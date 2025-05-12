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
        box.className = `pass-box ${slot.status === 'free' ? 'free' : 'occupied'}`;
        box.innerHTML = `
          <div class="symbol">${slot.status === 'free' ? 'O' : 'X'}</div>
          <div class="status-text">${slot.status === 'free' ? 'Free' : 'OUT @ ' + slot.time_out}</div>
          <div class="id-label">Pass ${i + 1}</div>
        `;
        container.appendChild(box);
      });
    });
}

document.getElementById('check-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const formData = new FormData(this);
  fetch('/check', {
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

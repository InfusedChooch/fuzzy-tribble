console.log("✅ rooms.js loaded");

function fetchRooms() {
  fetch('/admin_rooms')
    .then(r => r.json())
    .then(data => {
      console.log("🔁 drawing", data);
      drawTable(data);
    })
    .catch(err => console.error("❌ fetch failed:", err));
}

function drawTable(data) {
  const tbody = document.querySelector('#room-table tbody');
  if (!tbody) {
    console.error("❌ tbody not found");
    return;
  }

  tbody.innerHTML = '';
  data.forEach(r => {
    const tr = document.createElement('tr');

    // Room label with type tag
    const roomLink = document.createElement('a');
    roomLink.href = "#";
    roomLink.className = 'room-link';
    roomLink.textContent = r.room;
    roomLink.onclick = (e) => {
      e.preventDefault();
      openWindowRemembered(`/station_view/${r.room}`, `station-${r.room}`);
    };
    const roomCell = tr.insertCell();
    roomCell.appendChild(roomLink);

    // Add type label
    const label = document.createElement('span');
    label.textContent = r.type === 'station' ? ' Station' : ' Room';
    label.style.marginLeft = '8px';
    label.style.fontSize = '0.75em';
    label.style.padding = '2px 6px';
    label.style.borderRadius = '4px';
    label.style.background = r.type === 'station' ? '#e0f7fa' : '#e8f5e9';
    label.style.color = r.type === 'station' ? '#00796b' : '#33691e';
    roomCell.appendChild(label);

    // Toggle
    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.checked = r.active;
    toggle.onchange = () =>
      fetch('/admin_rooms', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: r.room, active: toggle.checked })
      }).then(fetchRooms);
    tr.insertCell().appendChild(toggle);

    // Dots: red = taken, blue = pending, green = free
    const dots = tr.insertCell();
    const totalSlots = r.taken + r.pending + r.free;

    for (let i = 0; i < r.taken; i++) {
      const d = document.createElement('span');
      d.className = 'dot taken'; // 🔴 red
      dots.appendChild(d);
    }

    for (let i = 0; i < r.pending; i++) {
      const d = document.createElement('span');
      d.className = 'dot pending'; // 🔵 blue
      dots.appendChild(d);
    }

    for (let i = 0; i < r.free; i++) {
      const d = document.createElement('span');
      d.className = 'dot free'; // 🟢 green
      dots.appendChild(d);
    }

    // Actions
    const actionCell = tr.insertCell();
    const menuBtn = document.createElement('button');
    menuBtn.textContent = '⋮';
    menuBtn.title = `Actions for ${r.room}`;
    menuBtn.onclick = () => showRoomActions(r.room);
    actionCell.appendChild(menuBtn);

    tbody.appendChild(tr);
  });
}

function addRoom() {
  const name = prompt("Enter new room/station name:");
  if (!name) return;

  fetch('/admin_rooms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ room: name.trim() })
  })
    .then(res => {
      if (!res.ok) throw new Error("Room add failed");
      return res.text();
    })
    .then(() => fetchRooms())
    .catch(err => console.error("❌ Add room error:", err));
}

function showRoomActions(room) {
  const popup = document.createElement('div');
  popup.style.position = 'fixed';
  popup.style.top = '20%';
  popup.style.left = '40%';
  popup.style.background = '#fff';
  popup.style.border = '1px solid #ccc';
  popup.style.padding = '1em';
  popup.style.zIndex = 9999;
  popup.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
  popup.style.minWidth = '250px';

  popup.innerHTML = `
    <strong>Actions for ${room}</strong><br><br>
    <button onclick="renameRoom('${room}')">📝 Rename</button>
    <button onclick="viewRoomStats('${room}')">📈 View Stats</button>
    <button onclick="resetRoom('${room}')">🔁 Reset</button>
    <button onclick="copyLink('${room}')">📋 Copy Link</button>
    <button onclick="deleteRoom('${room}')">🗑 Delete</button><br><br>
    <button onclick="this.parentElement.remove()">❌ Close</button>
  `;

  document.body.appendChild(popup);
}

function renameRoom(room) {
  const newName = prompt(`Rename room "${room}" to:`);
  if (newName && newName.trim() !== room) {
    fetch('/admin_rooms/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old: room, new: newName.trim() })
    })
      .then(res => {
        if (!res.ok) throw new Error("Rename failed");
        fetchRooms();
      })
      .catch(err => alert("❌ Rename error: " + err.message));
  }
}

function viewRoomStats(room) {
  fetch(`/admin_rooms/stats/${room}`)
    .then(res => res.json())
    .then(data => {
      alert(`📊 Stats for ${room}:\nActive passes: ${data.active}\nTotal today: ${data.count_today}`);
    })
    .catch(err => alert("❌ Failed to fetch stats: " + err.message));
}

function resetRoom(room) {
  if (!confirm(`Reset all passes for room "${room}" today?`)) return;

  fetch('/admin_rooms/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ room })
  })
    .then(res => res.json())
    .then(data => {
      alert(`✅ Reset complete. ${data.cleared} passes cleared.`);
      fetchRooms();
    })
    .catch(err => alert("❌ Reset failed: " + err.message));
}

function copyLink(room) {
  const link = `${window.location.origin}/station_view/${room}`;
  navigator.clipboard.writeText(link)
    .then(() => alert(`Copied: ${link}`))
    .catch(err => alert("Failed to copy"));
}

function deleteRoom(room) {
  if (!confirm(`Delete room "${room}" from the list?`)) return;

  fetch('/admin_rooms', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ room })
  })
    .then(() => fetchRooms())
    .catch(err => alert("❌ Delete failed: " + err.message));
}

function closeAllRooms() {
  fetch('/admin_rooms')
    .then(res => res.json())
    .then(data => {
      const activeRooms = data.filter(r => r.active).map(r => r.room);
      activeRooms.forEach(room => {
        fetch('/admin_rooms', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room, active: false })
        });
      });
      setTimeout(fetchRooms, 500); // small delay to ensure updates apply
    })
    .catch(err => alert("❌ Failed to close all: " + err.message));
}



window.onload = fetchRooms;
setInterval(fetchRooms, 5000);

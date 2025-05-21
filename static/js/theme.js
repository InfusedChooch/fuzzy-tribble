// theme.js — toggles dark mode and attaches gear icon

function toggleDarkMode() {
  document.body.classList.toggle("dark");
  localStorage.setItem("darkmode", document.body.classList.contains("dark"));
}

document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("darkmode") === "true") {
    document.body.classList.add("dark");
  }

  const container = document.createElement("div");
  container.style.position = "fixed";
  container.style.bottom = "10px";
  container.style.right = "10px";
  container.style.zIndex = 9999;
  container.style.display = "flex";
  container.style.gap = "6px";

  const moonBtn = document.createElement("button");
  moonBtn.innerHTML = "🌓";
  moonBtn.title = "Toggle Dark Mode";
  moonBtn.style.cssText = `
    font-size: 1.2em; padding: 4px 8px; border-radius: 8px;
    background: var(--btn-bg); color: white; border: none; cursor: pointer;
  `;
  moonBtn.onclick = toggleDarkMode;
  container.appendChild(moonBtn);

  const userRole = window.userRole || "";
  if (["teacher", "admin"].includes(userRole)) {
    const gearBtn = document.createElement("button");
    gearBtn.innerHTML = "⚙️";
    gearBtn.title = "Settings";
    gearBtn.style.cssText = moonBtn.style.cssText;
    gearBtn.onclick = () => {
      if (typeof openSettingsPopup === "function") {
        openSettingsPopup();
      } else {
        alert("Settings popup not available.");
      }
    };
    container.appendChild(gearBtn);
  }

  document.body.appendChild(container);
});

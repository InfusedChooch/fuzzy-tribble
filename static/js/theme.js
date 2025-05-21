// theme.js — toggles dark mode based on local storage
function toggleDarkMode() {
  document.body.classList.toggle("dark");
  localStorage.setItem("darkmode", document.body.classList.contains("dark"));
}

document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("darkmode") === "true") {
    document.body.classList.add("dark");
  }

const btn = document.createElement("button");
btn.innerHTML = "🌓"; // emoji only
btn.title = "Toggle Dark Mode";
btn.style.position = "fixed";
btn.style.bottom = "10px";
btn.style.right = "10px";
btn.style.zIndex = 9999;
btn.style.fontSize = "1.2em";
btn.style.padding = "4px 8px";
btn.style.borderRadius = "8px";
btn.style.background = "var(--btn-bg)";
btn.style.color = "white";
btn.style.border = "none";
btn.style.cursor = "pointer";
btn.onclick = toggleDarkMode;
document.body.appendChild(btn);

});

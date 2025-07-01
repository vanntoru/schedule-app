export async function loadEvents() {
  const resp = await fetch('/api/health');
  const data = await resp.json();
  const el = document.getElementById('events');
  if (el) {
    el.textContent = data.status;
  }
}

// load immediately when module is imported
loadEvents();

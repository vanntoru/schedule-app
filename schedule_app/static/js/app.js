/**
 * static/js/app.js
 *   ─ 今日の日付を UTC で計算し、/api/calendar から予定一覧を取得。
 *   ─ <div id="events"> にチップ（青ラベル）で描画。
 */
(async () => {
  /** YYYY-MM-DD (UTC) を返す */
  function todayUtcISO() {
    const d = new Date();
    const y = d.getUTCFullYear();
    const m = String(d.getUTCMonth() + 1).padStart(2, "0");
    const day = String(d.getUTCDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  /** Event[] を取得 */
  async function fetchEvents(dateStr) {
    const res = await fetch(`/api/calendar?date=${dateStr}`);
    if (!res.ok) {
      throw new Error(`Calendar API failed: ${res.status}`);
    }
    return res.json(); // [{ id, title, ... }]
  }

  /** チップ描画 */
  function render(events) {
    const wrap = document.getElementById("events");
    if (!wrap) return;
    wrap.innerHTML = "";
    for (const ev of events) {
      const chip = document.createElement("span");
      chip.className =
        "inline-block m-1 px-2 py-0.5 text-sm rounded bg-blue-100 text-blue-800";
      chip.textContent = ev.title;
      wrap.appendChild(chip);
    }
  }

  try {
    const events = await fetchEvents(todayUtcISO());
    render(events);
  } catch (err) {
    console.error(err);
  }
})();

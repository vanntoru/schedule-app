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

/* ──────────────────────────────────────────────────────────────
 * IndexedDB initialisation — schedule_app (version 2)
 * 仕様書 §3（IndexedDB schedule_app, ver 2）および
 * ステップ 21 の要件に対応
 * ────────────────────────────────────────────────────────── */

const DB_NAME   = 'schedule_app';
const DB_VERSION = 2;

/**
 * Open (or upgrade) the IndexedDB database and expose a Promise
 *   window.dbReady → Promise<IDBDatabase>
 *
 * Object stores — created only when they don’t exist:
 *   • tasks    (keyPath: 'id')
 *   • blocks   (keyPath: 'id')
 *   • schedule (keyPath: 'date')
 */
export const openDb = (() => {
  let _promise = null;

  return function openDb() {
    if (_promise) return _promise;

    _promise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);

      req.onupgradeneeded = (event) => {
        /** @type {IDBDatabase} */
        const db = req.result;

        // version‑aware migration
        switch (event.oldVersion) {
          case 0: {             // fresh install
            db.createObjectStore('tasks',    { keyPath: 'id'   });
            db.createObjectStore('blocks',   { keyPath: 'id'   });
            db.createObjectStore('schedule', { keyPath: 'date' });
            break;
          }
          case 1: {             // ← ver 1 → ver 2 migration例
            if (!db.objectStoreNames.contains('schedule')) {
              db.createObjectStore('schedule', { keyPath: 'date' });
            }
            break;
          }
          // future migrations: fall through
        }
      };

      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });

    return _promise;
  };
})();

// Kick off immediately so the DB appears in DevTools without user action
window.dbReady = openDb();

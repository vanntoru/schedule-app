/**
 * @typedef {{ apply: () => void, revert: () => void }} Command
 */

/**
 * static/js/app.js
 *   ─ 今日の日付を UTC で計算し、/api/calendar から予定一覧を取得。
 *   ─ window.renderAllDay(events) で All-day タイムラインを描画。
 */

/* ──────────────  Utilities (shared) ────────────── */
/**
 * 今日の日付を **UTC 基準** の YYYY-MM-DD 文字列で返す。
 * <input type="date"> の value にそのまま渡せる。
 */
export function todayUtcISO() {
  const d = new Date();
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

(async () => {

  /** Event[] を取得 */
  async function fetchEvents(dateStr) {
    const res = await fetch(`/api/calendar?date=${dateStr}`);

    if (res.status === 401) {
      // Redirect to login for unauthenticated users, except when running
      // under Playwright where `navigator.webdriver` is true. Playwright
      // should remain on the current page so tests are not interrupted.
      if (!navigator.webdriver) {
        window.location.assign('/login');
      }
      throw new Error('Calendar API unauthorized');
    }

    if (!res.ok) {
      throw new Error(`Calendar API failed: ${res.status}`);
    }

    return res.json(); // [{ id, title, ... }]
  }

  try {
    const events = await fetchEvents(todayUtcISO());
    window.renderAllDay(events);
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

/* ─────────────────── 既存コードの下 (DnD 即上あたり) ────────────────── */
//////////////////////////////////////////////////////////////////////
//  SECTION: Task loading / rendering
//////////////////////////////////////////////////////////////////////

async function loadAndRenderTasks() {
  try {
    const res   = await fetch('/api/tasks');
    const tasks = await res.json();          // [{id,title,…}, …]

    const pane       = document.getElementById('task-pane');
    const emptyLabel = document.getElementById('task-empty');
    pane.querySelectorAll('.task-card').forEach((n) => n.remove());

    if (!tasks.length) {
      emptyLabel.classList.remove('hidden');
      return;
    }
    emptyLabel.classList.add('hidden');

    for (const t of tasks) {
      const card = document.createElement('div');
      card.className =
        'task-card p-2 bg-white rounded shadow border ' +
        'cursor-grab select-none hover:bg-gray-50 ' +
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400';
      card.setAttribute('draggable', 'true');
      card.setAttribute('role', 'listitem');
      card.setAttribute('tabindex', '0');
      card.dataset.taskId = t.id;
      card.dataset.taskTitle = t.title;
      card.textContent    = `${t.title} (${t.duration_min}m)`;
      pane.appendChild(card);
    }
    applyContrastClasses();
  } catch (err) {
    console.error('[tasks] failed to load', err);
  }
}

/* DOMContentLoaded → まずタスクを描画 */
document.addEventListener('DOMContentLoaded', () => {
  loadAndRenderTasks();
});

// Ensure a time grid exists for tests or pages missing it
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('#time-grid')) return;

  const grid = document.createElement('section');
  grid.id = 'time-grid';
  grid.setAttribute('role', 'grid');
  grid.setAttribute('aria-label', '24-hour schedule grid');
  grid.className = 'grid border border-gray-300 grid-cols-[70px_1fr] flex-1';

  for (let i = 0; i < 144; i++) {
    const ts = i * 10;
    const h = String(Math.floor(ts / 60)).padStart(2, '0');
    const m = String(ts % 60).padStart(2, '0');

    const label = document.createElement('div');
    label.className = 'hour-label p-1 text-right text-xs font-mono';
    if (m !== '00') label.classList.add('opacity-0');
    label.textContent = `${h}:${m}`;

    const slot = document.createElement('div');
    slot.className =
      'slot border-b border-gray-200 hover:bg-blue-50 cursor-pointer ' +
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400';
    slot.setAttribute('role', 'gridcell');
    slot.setAttribute('tabindex', '0');
    slot.dataset.slotIndex = String(i);

    grid.appendChild(label);
    grid.appendChild(slot);
  }

  document.body.appendChild(grid);
  applyContrastClasses();
});

/* ────────────────────────────────────────────────────────────────
 *  Drag & Drop support for task cards ⇄ time‑grid slots
 *  Spec §8.1  “.dragging → opacity:0.5”  /  drop target ring‑blue‑400
 * ────────────────────────────────────────────────────────────────
 *
 *  1. すでに fetch / IndexedDB 初期化コードがある部分の **末尾** に
 *     以下の DnD 追加実装を貼り付けてください。
 *
 *  2.   DOM 依存
 *      - タスクカード   : <div class="task-card" draggable="true" data-task-id="…">
 *      - グリッドセル   : <div class="slot" data-slot-index="0"> … </div>
 *        （テンプレートや JS 生成時に `data-slot-index` を付与済み）
 *
 *  3.  状態操作
 *      - slotOccupied(index)          ▶︎ Boolean
 *      - markSlot(index, taskId)      ▶︎ DOM ＆ IndexedDB を更新
 *      - unmarkSlot(index)            ▶︎ 〃
 *      ※ これらヘルパは既存 schedule モジュールに stub がある想定。
 *        未実装ならファイル末尾にシンプルな Map ベースで実装して構いません。
 * ----------------------------------------------------------------*/

(() => {
  /* current dragging element & origin slot */
  let draggingCard = null;
  let originIndex  = null;

  /* helper — true if e.target is a grid slot */
  const asSlot = (el) => el?.closest?.('[data-slot-index]');

  // History is managed globally via _history / _ptr

  /* ---------- dragstart ------------------------------------------------ */
  document.addEventListener('dragstart', (e) => {
    const card = e.target.closest('.task-card');
    if (!card) return;

    draggingCard = card;
    originIndex  = parseInt(card.dataset.slotIndex ?? '-1', 10) || null;

    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', card.dataset.taskId);
    card.classList.add('dragging');          // opacity‑50  (Tailwind)
  });

  /* ---------- dragover / dragenter ------------------------------------- */
  document.addEventListener('dragover', (e) => {
    const slot = asSlot(e.target);
    if (!slot) return;

    const idx = parseInt(slot.dataset.slotIndex, 10);
    if (!slotOccupied(idx)) {
      e.preventDefault();                    // enable drop
      slot.classList.add('ring-2', 'ring-blue-400');
    }
  });

  document.addEventListener('dragleave', (e) => {
    const slot = asSlot(e.target);
    slot?.classList.remove('ring-2', 'ring-blue-400');
  });

  /* ---------- drop ----------------------------------------------------- */
  document.addEventListener('drop', (e) => {
    const slot = asSlot(e.target);
    if (!slot) return;

    const nextIdx = parseInt(slot.dataset.slotIndex, 10);
    if (slotOccupied(nextIdx)) return;

    e.preventDefault();

    // ----- state snapshot -----
    const card = draggingCard;
    const prevSlot = originIndex !== null
      ? document.querySelector(`[data-slot-index="${originIndex}"]`)
      : null;

    // ----- perform move -----
    slot.appendChild(card);
    card.dataset.slotIndex = nextIdx;
    markSlot(nextIdx, card.dataset.taskId);
    if (originIndex !== null) unmarkSlot(originIndex);

  // ----- record command -----
  pushCommand({
      apply() {              // Redo
        slot.appendChild(card);
        card.dataset.slotIndex = nextIdx;
        markSlot(nextIdx, card.dataset.taskId);
        if (prevSlot) unmarkSlot(parseInt(prevSlot.dataset.slotIndex, 10));
      },
      revert() {             // Undo
        if (prevSlot) {
          prevSlot.appendChild(card);
          card.dataset.slotIndex = originIndex;
          markSlot(originIndex, card.dataset.taskId);
        } else {
          // 元は side‑pane にあったカード
          document.getElementById('task-pane').appendChild(card);
          card.removeAttribute('data-slot-index');
        }
        unmarkSlot(nextIdx);
      },
      skipRender: true,
  });

    // ----- visual cleanup -----
    slot.classList.remove('ring-2', 'ring-blue-400');
  });

  /* ---------- dragend -------------------------------------------------- */
  document.addEventListener('dragend', () => {
    draggingCard?.classList.remove('dragging');
    draggingCard = null;
    originIndex  = null;

    /* clear any stray highlights */
    document
      .querySelectorAll('.slot.ring-blue-400')
      .forEach((el) => el.classList.remove('ring-2', 'ring-blue-400'));
  });

  /* ---------- minimal fallback impl. ----------------------------------- */
  /* 既成ヘルパが無い場合の簡易実装（Map ベース）——重複登録にも強い */
  const gridState = new Map();   // key: slotIndex, value: taskId

  function slotOccupied(i) {
    return gridState.has(i);
  }
function markSlot(i, tid) {
    gridState.set(i, tid);
    document
      .querySelector(`[data-slot-index="${i}"]`)
      ?.classList.add('grid-slot--busy');
    applyContrastClasses();   // ★ 追加
    /* TODO: IndexedDB schedule save (phase‑1) */
}
  function unmarkSlot(i) {
    gridState.delete(i);
    document
      .querySelector(`[data-slot-index="${i}"]`)
      ?.classList.remove('grid-slot--busy');
  }
})();

// ---------------------------------------------------------------------------
// Schedule grid loading and history (Undo / Redo)
// ---------------------------------------------------------------------------

/* ===== Utility: rotate grid by N slots (positive = right) ============ */
function rotate(grid, shift) {
  const n = grid.length;
  const g = new Array(n);
  for (let i = 0; i < n; i++) {
    g[(i + shift + n) % n] = grid[i];
  }
  return g;
}

/* ===== New: convert UTC‑grid → Local‑grid ============================ */
function shiftGridToLocalTZ(grid) {
  // 例) JST (UTC+9) なら getTimezoneOffset() = -540 → offsetMin = +540
  const offsetMin  = -new Date().getTimezoneOffset();   // (+) if east of UTC
  const offsetSlot = Math.round(offsetMin / 10);        // 10 分 = 1 slot
  return rotate(grid, offsetSlot);
}

/** Adjust meta start/end slot to local timezone offset. */
function shiftMetaToLocalTZ(meta) {
  const offsetMin  = -new Date().getTimezoneOffset();
  const offsetSlot = Math.round(offsetMin / 10);
  const result = {};
  for (const [id, m] of Object.entries(meta || {})) {
    const s = Number.isInteger(m.start_slot)
      ? (m.start_slot + offsetSlot + 144) % 144
      : m.start_slot;
    const e = Number.isInteger(m.end_slot)
      ? (m.end_slot + offsetSlot + 144) % 144
      : m.end_slot;
    result[id] = { ...m, start_slot: s, end_slot: e };
  }
  return result;
}

let scheduleGrid = new Array(144).fill(0); // current grid state
let scheduleMeta = { tasks: {}, events: {} };

const HISTORY_LIMIT = 20;
const _history = [];
let _ptr = -1; // points to last applied command

/** Render the grid based on `scheduleGrid` values. */
function renderGrid() {
  document.querySelectorAll('.slot[data-slot-index]').forEach((el) => {
    const idx = Number(el.dataset.slotIndex);
    const raw = scheduleGrid[idx] ?? 0;
    let type = 0;
    if (typeof raw === 'object') {
      if (raw.task_id) type = 2;
      else if (raw.event_id || raw.busy) type = 1;
    } else {
      type = raw;
    }

    [...el.classList].forEach((cls) => {
      if (
        cls.startsWith('bg-') ||
        cls === 'grid-slot--busy' ||
        cls === 'busy-strong'
      ) {
        el.classList.remove(cls);
      }
    });
    el.textContent = '';

    let meta = null;
    if (typeof raw === 'object') {
      if (raw.task_id) meta = scheduleMeta.tasks[raw.task_id];
      if (raw.event_id) meta = scheduleMeta.events[raw.event_id];
    }

    if (meta && meta.color) {
      el.classList.add(meta.color);
    } else if (type === 1) {
      el.classList.add('bg-gray-200');
    } else if (type === 2) {
      el.classList.add('bg-green-200');
    }
    if (type === 1 || type === 2) el.classList.add('grid-slot--busy');
    if (meta && meta.title) el.textContent = meta.title;
    el.classList.remove('border-t-0', 'border-b-0');
  });

  function groupBlocks(metaMap) {
    Object.values(metaMap || {}).forEach((m) => {
      const s = Number(m.start_slot);
      const e = Number(m.end_slot);
      if (!Number.isInteger(s) || !Number.isInteger(e)) return;
      for (let i = s; i <= e; i++) {
        const slot = document.querySelector(`[data-slot-index="${i}"]`);
        if (!slot) continue;
        if (i === s) {
          slot.textContent = m.title || '';
        } else {
          slot.textContent = '';
          slot.classList.add('border-t-0');
        }
        if (i < e) slot.classList.add('border-b-0');
      }
    });
  }

  groupBlocks(scheduleMeta.events);
  groupBlocks(scheduleMeta.tasks);
  /* Reduced-contrast ON なら新セルにも busy-strong を再付与 */
  applyContrastClasses();
}

/** Persist the current grid. Placeholder for IndexedDB integration. */
function saveState() {
  const input = document.querySelector('#input-date');
  const date = input && input.value ? input.value : todayUtcISO();
  if (!date) return;

  window.dbReady.then((db) => {
    const tx = db.transaction('schedule', 'readwrite');
    const store = tx.objectStore('schedule');
    const record = { date, grid: scheduleGrid.slice(), meta: scheduleMeta };
    store.put(record);
  }).catch((err) => {
    console.error('[IndexedDB] save failed', err);
  });
}

/** Load grid data from the server for the given `date` via GET. */
async function loadGridFromServer(date) {
  let res;
  try {
    res = await fetch(`/api/schedule/generate?date=${date}&algo=greedy`);
    if (!res.ok) {
      throw new Error(`Schedule API failed: ${res.status}`);
    }
  } catch (err) {
    // Fallback to IndexedDB if available
    try {
      const db = await window.dbReady;
      const tx = db.transaction('schedule', 'readonly');
      const store = tx.objectStore('schedule');
      const rec = await new Promise((resolve, reject) => {
        const r = store.get(date);
        r.onsuccess = () => resolve(r.result);
        r.onerror = () => reject(r.error);
      });
      if (rec && rec.grid) {
        scheduleMeta = rec.meta || { tasks: {}, events: {} };
        scheduleGrid = rec.grid.slice();

        // ───── reconstruct missing event metadata ─────
        if (!scheduleMeta.events || Object.keys(scheduleMeta.events).length === 0) {
          const events = {};
          for (let i = 0; i < scheduleGrid.length; i++) {
            const cell = scheduleGrid[i];
            if (typeof cell === 'object' && cell.event_id) {
              const id = cell.event_id;
              if (!events[id]) {
                events[id] = { id, start_slot: i, end_slot: i, color: 'bg-gray-200' };
              } else {
                events[id].end_slot = i;
              }
            }
          }
          scheduleMeta.events = events;
          saveState();
        }

        renderGrid();
        return { grid: scheduleGrid, unplaced: [] };
      }
    } catch (dbErr) {
      console.error('[IndexedDB] load failed', dbErr);
    }
    throw err;
  }

  const raw = await res.json();
  const slots = Array.isArray(raw)
    ? raw
    : Array.isArray(raw.slots)
      ? raw.slots
      : Array.isArray(raw.grid)
        ? raw.grid
        : (() => { throw new Error('Malformed Grid'); })();
  const unplaced = Array.isArray(raw.unplaced) ? raw.unplaced : [];

  scheduleMeta = {
    tasks: shiftMetaToLocalTZ(raw.tasks || {}),
    events: shiftMetaToLocalTZ(raw.events || {}),
  };

  /** ★ ここでローカルタイム位置へシフト ★ */
  scheduleGrid = shiftGridToLocalTZ(slots);

  renderGrid();
  saveState();
  return { grid: scheduleGrid, unplaced };
}

/** Restore the grid from a saved array. */
function restoreGrid(prev) {
  scheduleGrid = prev.slice();
  renderGrid();
  saveState();
}

/** Push a command object onto the history stack. */
function pushCommand(cmd) {
  _history.splice(_ptr + 1); // drop redo history
  _history.push(cmd);
  if (_history.length > HISTORY_LIMIT) _history.shift();
  _ptr = _history.length - 1;
  updateUndoRedoButtons();
}

/** Undo the last command. */
function doUndo() {
  if (_ptr < 0) return;
  const cmd = _history[_ptr];
  _ptr--;
  cmd.revert();
  if (!cmd.skipRender) {
    renderGrid();
    saveState();
  }
  updateUndoRedoButtons();
}

/** Redo the next command. */
function doRedo() {
  if (_ptr + 1 >= _history.length) return;
  _ptr++;
  const cmd = _history[_ptr];
  cmd.apply();
  if (!cmd.skipRender) {
    renderGrid();
    saveState();
  }
  updateUndoRedoButtons();
}


/** Highlight unplaced tasks and show toast messages. */
function showUnplacedTasks(unplacedIds) {
  const pane = document.getElementById('task-pane');
  if (!pane) return;

  pane.querySelectorAll('.task-card').forEach((card) => {
    card.classList.remove('bg-red-300', 'ring-2', 'ring-red-500', 'line-through');
  });

  for (const id of unplacedIds || []) {
    const card = pane.querySelector(`[data-task-id="${id}"]`);
    if (!card) continue;
    card.classList.add('bg-red-300', 'ring-2', 'ring-red-500', 'line-through');
    const title = card.dataset.taskTitle || card.textContent.trim();
    showToast('未配置: ' + title);
  }
}

/** Generate schedule and record undo information. */
async function generateSchedule(date) {
  const previousGrid = scheduleGrid.slice();
  const { unplaced } = await loadGridFromServer(date);
  showUnplacedTasks(unplaced);
  pushCommand({
    apply: async () => {
      const { unplaced } = await loadGridFromServer(date);
      showUnplacedTasks(unplaced);
    },
    revert: () => {
      restoreGrid(previousGrid);
      showUnplacedTasks([]);
    },
  });
}

// Expose undo/redo for keyboard handlers or UI buttons
window.doUndo = doUndo;
window.doRedo = doRedo;

// ❶ キーボードショートカット
document.addEventListener('keydown', (e) => {
  const k = e.key.toLowerCase();
  if (!e.ctrlKey) return;
  if (k === 'z') { e.preventDefault(); doUndo(); updateUndoRedoButtons(); }
  if (k === 'y') { e.preventDefault(); doRedo(); updateUndoRedoButtons(); }
});

// ❷ ヘッダー ← / → ボタン（id=undo-btn / redo-btn）
const undoBtn = document.getElementById('undo-btn');
const redoBtn = document.getElementById('redo-btn');

undoBtn?.addEventListener('click', () => { doUndo(); updateUndoRedoButtons(); });
redoBtn?.addEventListener('click', () => { doRedo(); updateUndoRedoButtons(); });

export function updateUndoRedoButtons() {
  const undoActive = _ptr >= 0;
  const redoActive = _ptr + 1 < _history.length;
  undoBtn.disabled = !undoActive;
  redoBtn.disabled = !redoActive;

  const toggle = (btn, active) => {
    btn.classList.toggle('text-gray-400', !active);
    btn.classList.toggle('border-gray-300', !active);
    btn.classList.toggle('cursor-not-allowed', !active);
    btn.classList.toggle('opacity-50', !active);

    btn.classList.toggle('text-black', active);
    btn.classList.toggle('border-black', active);
  };
  toggle(undoBtn, undoActive);
  toggle(redoBtn, redoActive);
}

document.addEventListener('DOMContentLoaded', updateUndoRedoButtons);

// ---------------------------------------------------------------------------
// Schedule Generate button handler
// Spec §6, §7 で定義した <div id="time-grid">…</div> を更新する
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const btnGenerate = document.querySelector('#btn-generate');
  const inputDate  = document.querySelector('#input-date');

  /* ★ 追加 ① — ピッカーがあれば初期値を今日 (UTC) に設定 */
  if (inputDate && !inputDate.value) {
    inputDate.value = todayUtcISO();
  }

  /* ★★ 追加 ② — ピッカー変更時に All‑day 予定を再取得 ★★ */
  inputDate?.addEventListener('change', async () => {
    const ymd = inputDate.value;
    if (!ymd) return;
    try {
      const events = await fetch(`/api/calendar?date=${ymd}`).then((r) =>
        r.json(),
      );
      window.renderAllDay(events);
    } catch (err) {
      console.error('[calendar] reload failed', err);
    }
  });

  /* ★ 追加 ② — API 叩く際、ピッカーが無い場合は todayUtcISO() を使う */
  btnGenerate?.addEventListener('click', async () => {
    const ymd = inputDate ? inputDate.value : todayUtcISO();

    if (!ymd) {
      alert('日付を選択してください');
      return;
    }
    try {
      /* 1) スケジュール生成（/api/schedule/generate） */
      await generateSchedule(ymd);

      /* 2) All-day 予定も最新化 */
      const events = await fetch(`/api/calendar?date=${ymd}`).then((r) => r.json());
      window.renderAllDay(events);
    } catch (err) {
      console.error(err);
      alert(`スケジュール生成に失敗しました\n${err.message ?? err}`);
    }
  });
});

/**
 * 画面中央下に 4 秒間表示する Toast
 * @param {string} message
 */
function showToast(message) {
  // Remove any existing toast so only one is visible at a time
  document
    .querySelectorAll('.schedule-toast')
    .forEach((el) => el.remove());

  const toast = document.createElement('div');
  toast.textContent = message;
  toast.className =
    'schedule-toast fixed bottom-4 left-1/2 -translate-x-1/2 z-50 ' +
    'bg-red-600 text-white px-4 py-2 rounded shadow-lg ' +
    'opacity-0 transition-opacity duration-300';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');

  document.body.appendChild(toast);

  /* フェードイン */
  requestAnimationFrame(() => toast.classList.remove('opacity-0'));

  /* 4 秒後フェードアウト → 削除 */
  setTimeout(() => {
    toast.classList.add('opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}


/* === Reduced-contrast 検知 → busy-strong クラス切替 =============== */
const mqReduced = window.matchMedia('(prefers-contrast: less)');

/** busy / task 要素に busy-strong を付け外しする */
function applyContrastClasses() {
  const strong = mqReduced.matches;
  document
    .querySelectorAll('.grid-slot--busy, .task-card')
    .forEach((el) =>
      el.classList.toggle('busy-strong', strong),
    );
}

/* 初期化 & OS 設定変更に追随 */
mqReduced.addEventListener('change', applyContrastClasses);
document.addEventListener('DOMContentLoaded', applyContrastClasses);   // ← グリッド生成後


// Service Worker registration
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js", { scope: "/" })
    .then(reg => console.log("SW registered:", reg.scope))
    .catch(err => console.error("SW registration failed:", err));
}

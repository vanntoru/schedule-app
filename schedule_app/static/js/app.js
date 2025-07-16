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
 * Fetch JSON from the REST API with unified error handling.
 * Redirects to /login on 401 unless running under Playwright.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<any>}
 * @throws {Error} when the request fails
 */
export async function apiFetch(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new Error('Network error');
  }

  if (res.status === 401) {
    if (!navigator.webdriver) {
      window.location.assign('/login');
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    let message = res.statusText || 'Request failed';
    try {
      const data = await res.clone().json();
      message = data.detail || data.message || message;
    } catch (_) {
      // ignore JSON parse errors
    }
    throw new Error(message);
  }

  if (res.status === 204) {
    return null;
  }

  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    return res.json();
  }
  return res.text();
}
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

/**
 * Extract only all-day events from an array.
 *
 * @param {Array<{all_day?: boolean}>} events
 * @returns {any[]}
 */
export function filterAllDay(events) {
  return (events || []).filter(ev => ev.all_day);
}

/**
 * Remove all existing <li> elements from the all-day timeline.
 */
export function resetAllDayTimeline() {
  const ul = document.getElementById('all-day-timeline');
  if (ul) ul.innerHTML = '';
}

(async () => {

  /** Event[] を取得 */
  async function fetchEvents(dateStr) {
    return apiFetch(`/api/calendar?date=${dateStr}`);
  }

  try {
    const events = await fetchEvents(todayUtcISO());
    const allDay = filterAllDay(events);
    window.allDayEvents = allDay;
    resetAllDayTimeline();
    window.renderAllDay(allDay);
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
    const tasks = await apiFetch('/api/tasks'); // [{id,title,…}, …]

    const pane       = document.getElementById('task-pane');
    const list       = document.getElementById('task-list');
    const emptyLabel = document.getElementById('task-empty');
    const tmpl       = document.getElementById('task-card-template');

    list.querySelectorAll('.task-card').forEach((n) => n.remove());

    if (!tasks.length) {
      emptyLabel.classList.remove('hidden');
      return;
    }
    emptyLabel.classList.add('hidden');

    for (const t of tasks) {
      /** @type {HTMLElement} */
      let card;
      if (tmpl && tmpl.content.firstElementChild) {
        card = tmpl.content.firstElementChild.cloneNode(true);
      } else {
        card = document.createElement('div');
        card.className =
          'task-card p-2 bg-white rounded shadow border ' +
          'cursor-grab select-none hover:bg-gray-50 ' +
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400';
        card.setAttribute('draggable', 'true');
        card.setAttribute('role', 'listitem');
        card.setAttribute('tabindex', '0');

        const span = document.createElement('span');
        span.className = 'task-label';
        card.appendChild(span);
        const btnEdit = document.createElement('button');
        btnEdit.type = 'button';
        btnEdit.className = 'edit-task ml-2 border rounded px-1 text-xs';
        btnEdit.textContent = '編集';
        card.appendChild(btnEdit);
        const btnDel = document.createElement('button');
        btnDel.type = 'button';
        btnDel.className = 'delete-task ml-2 border rounded px-1 text-xs';
        btnDel.textContent = '削除';
        card.appendChild(btnDel);
      }
      card.dataset.taskId = t.id;
      card.dataset.taskTitle = t.title;
      card.dataset.taskCategory = t.category || '';
      card.dataset.taskDuration = t.duration_min;
      card.dataset.taskPriority = t.priority;
      if (t.earliest_start_utc) {
        card.dataset.taskEarliest = t.earliest_start_utc;
      } else {
        delete card.dataset.taskEarliest;
      }

      const label = card.querySelector('.task-label') || card;
      label.textContent = `${t.title} (${t.duration_min}m)`;
      list.appendChild(card);
    }
    applyContrastClasses();
  } catch (err) {
    console.error('[tasks] failed to load', err);
    showToast(err.message ?? err);
  }
}

/* DOMContentLoaded → まずタスクを描画 */
document.addEventListener('DOMContentLoaded', () => {
  loadAndRenderTasks();
});

// ---------------------------------------------------------------------------
// Simple tab switching for Tasks / Blocks panels
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('[data-tab]');
  const panes = {
    'task-pane': document.getElementById('task-pane'),
    'blocks-panel': document.getElementById('blocks-panel'),
  };

  function activate(id) {
    for (const [pid, el] of Object.entries(panes)) {
      if (!el) continue;
      if (pid === id) {
        el.classList.remove('hidden');
      } else {
        el.classList.add('hidden');
      }
    }

    buttons.forEach((btn) => {
      const active = btn.dataset.tab === id;
      btn.classList.toggle('border-blue-600', active);
      btn.classList.toggle('border-transparent', !active);
    });
  }

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => activate(btn.dataset.tab));
  });

  activate('task-pane');
});

// Sheets Import button handler
document.addEventListener('DOMContentLoaded', () => {
  const btnImport = document.getElementById('btn-import-sheets');
  if (!btnImport) return;
  btnImport.addEventListener('click', async () => {
    try {
      await apiFetch('/api/tasks/import', { method: 'POST' });
      await loadAndRenderTasks();
    } catch (err) {
      console.error('tasks import failed', err);
      if (err && err.message === 'Unauthorized') {
        return; // Redirect handled by apiFetch
      }
      showToast(err.message ?? err);
    }
  });
});

// Clear Sheets cache button handler
document.addEventListener('DOMContentLoaded', () => {
  const btnClear = document.getElementById('btn-clear-cache');
  if (!btnClear) return;
  btnClear.addEventListener('click', async () => {
    try {
      await apiFetch('/api/tasks/cache', { method: 'DELETE' });
      showToast('Cache cleared');
    } catch (err) {
      console.error('cache clear failed', err);
      if (err && err.message === 'Unauthorized') {
        return;
      }
      showToast(err.message ?? err);
    }
  });
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
          document.getElementById('task-list').appendChild(card);
          card.removeAttribute('data-slot-index');
        }
        unmarkSlot(nextIdx);
      },
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

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.delete-task');
    if (!btn) return;

    const card = btn.closest('.task-card');
    if (!card) return;

    if (!confirm('このタスクを削除しますか?')) return;

    try {
      await apiFetch(`/api/tasks/${card.dataset.taskId}`, { method: 'DELETE' });
    } catch (err) {
      console.error('task delete failed', err);
      alert(err.message ?? err);
      return;
    }

    if (card.dataset.slotIndex) {
      unmarkSlot(parseInt(card.dataset.slotIndex, 10));
    }

    card.remove();

    const list = document.getElementById('task-list');
    if (list && !list.querySelector('.task-card')) {
      document.getElementById('task-empty')?.classList.remove('hidden');
    }
  });
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

let scheduleGrid = new Array(144).fill(0); // current grid state

const HISTORY_LIMIT = 20;
const _history = [];
let _ptr = -1; // points to last applied command

/** Render the grid based on `scheduleGrid` values. */
function renderGrid() {
  document.querySelectorAll('.slot[data-slot-index]').forEach((el) => {
    const idx = Number(el.dataset.slotIndex);
    const raw = scheduleGrid[idx] ?? 0;
    const val = typeof raw === 'object'
      ? raw.task ? 2 : raw.busy ? 1 : 0
      : raw;

    /* ---- 背景色と busy クラスをリセット ---- */
    el.classList.remove(
      'bg-gray-200',
      'bg-green-200',
      'bg-blue-500',
      'grid-slot--busy',
    );
    switch (val) {
      case 1:
        el.classList.add('bg-gray-200');
        el.classList.add('grid-slot--busy');
        break;
      case 2:
        el.classList.add('bg-green-200');
        el.classList.add('grid-slot--busy');
        break;
      default:
    }
  });
  /* Reduced-contrast ON なら新セルにも busy-strong を再付与 */
  applyContrastClasses();
}

/** Persist the current grid. Placeholder for IndexedDB integration. */
function saveState() {
  // TODO: implement persistence
}

/** Load grid data from the server for the given `date`. */
async function loadGridFromServer(date) {
  const raw = await apiFetch(
    `/api/schedule/generate?date=${date}&algo=greedy`,
    { method: 'POST' },
  );
  const slots = Array.isArray(raw)
    ? raw
    : Array.isArray(raw.slots)
      ? raw.slots
      : Array.isArray(raw.grid)
        ? raw.grid
        : (() => { throw new Error('Malformed Grid'); })();
  const unplaced = Array.isArray(raw.unplaced) ? raw.unplaced : [];

  const utcGrid = slots.map((s) => {
    if (typeof s === 'number') return s;
    if (s.busy === true) return 1;
    if (s.task === true) return 2;
    return 0;
  });

  /** ★ ここでローカルタイム位置へシフト ★ */
  scheduleGrid = shiftGridToLocalTZ(utcGrid);

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
  renderGrid();
  saveState();
  updateUndoRedoButtons();
}

/** Redo the next command. */
function doRedo() {
  if (_ptr + 1 >= _history.length) return;
  _ptr++;
  const cmd = _history[_ptr];
  cmd.apply();
  renderGrid();
  saveState();
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
      const events = await apiFetch(`/api/calendar?date=${ymd}`);
      const allDay = filterAllDay(events);
      window.allDayEvents = allDay;
      resetAllDayTimeline();
      window.renderAllDay(allDay);
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
      const events = await apiFetch(`/api/calendar?date=${ymd}`);
      const allDay = filterAllDay(events);
      window.allDayEvents = allDay;
      resetAllDayTimeline();
      window.renderAllDay(allDay);
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

// ---------------------------------------------------------------------------
// Task creation modal handlers
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const btnAdd    = document.getElementById('btn-add-task');
  const modal     = document.getElementById('task-modal');
  const form      = document.getElementById('task-form');
  const btnCancel = document.getElementById('task-cancel');
  const list      = document.getElementById('task-list');

  /**
   * Open the modal and focus the first input field.
   */
  function openModal() {
    modal.showModal();
    const first = modal.querySelector('input, select, textarea');
    first?.focus();
  }

  if (!btnAdd || !modal || !form) return;

  btnAdd.addEventListener('click', () => {
    form.reset();
    document.getElementById('task-id').value = '';
    form
      .querySelectorAll('[aria-invalid]')
      .forEach((el) => el.removeAttribute('aria-invalid'));
    openModal();
  });

  btnCancel?.addEventListener('click', () => {
    modal.close();
  });

  modal.addEventListener('close', () => {
    form
      .querySelectorAll('[aria-invalid]')
      .forEach((el) => el.removeAttribute('aria-invalid'));
  });

  // Close modal on ESC key
  modal.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      modal.close();
    }
  });

  list?.addEventListener('click', (e) => {
    const btn = e.target.closest('.edit-task');
    if (!btn) return;

    const card = btn.closest('.task-card');
    if (!card) return;

    document.getElementById('task-id').value = card.dataset.taskId;
    document.getElementById('task-title').value = card.dataset.taskTitle;
    document.getElementById('task-category').value = card.dataset.taskCategory || '';
    document.getElementById('task-duration').value = card.dataset.taskDuration;
    document.getElementById('task-priority').value = card.dataset.taskPriority;

    const earliest = card.dataset.taskEarliest;
    if (earliest) {
      const hhmm = new Date(earliest).toISOString().substring(11, 16);
      document.getElementById('task-earliest').value = hhmm;
    } else {
      document.getElementById('task-earliest').value = '';
    }

    form
      .querySelectorAll('[aria-invalid]')
      .forEach((el) => el.removeAttribute('aria-invalid'));
    openModal();
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const titleEl = document.getElementById('task-title');
    const catEl   = document.getElementById('task-category');
    const durEl   = document.getElementById('task-duration');
    const priEl   = document.getElementById('task-priority');
    const earEl   = document.getElementById('task-earliest');

    const title = titleEl.value.trim();
    const duration = parseInt(durEl.value, 10);

    titleEl.removeAttribute('aria-invalid');
    durEl.removeAttribute('aria-invalid');

    if (!title) {
      titleEl.setAttribute('aria-invalid', 'true');
      alert('タイトルを入力してください');
      titleEl.focus();
      return;
    }

    if (!Number.isFinite(duration) || duration % 5 !== 0) {
      durEl.setAttribute('aria-invalid', 'true');
      alert('所要時間は5分単位で入力してください');
      durEl.focus();
      return;
    }

    const payload = {
      title: titleEl.value,
      category: catEl.value,
      duration_min: duration,
      duration_raw_min: duration,
      priority: priEl.value,
    };

    if (earEl.value) {
      const iso = new Date(`1970-01-01T${earEl.value}:00Z`).toISOString().replace('.000Z', 'Z');
      payload.earliest_start_utc = iso;
    }

    const taskId = document.getElementById('task-id').value;

    try {
      const url = taskId ? `/api/tasks/${taskId}` : '/api/tasks';
      const method = taskId ? 'PUT' : 'POST';
      await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      modal.close();
      form.reset();
      await loadAndRenderTasks();
    } catch (err) {
      console.error('task create failed', err);
      alert(err.message ?? err);
    }
  });
});


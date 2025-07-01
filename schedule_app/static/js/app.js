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
        'cursor-grab select-none hover:bg-gray-50';
      card.setAttribute('draggable', 'true');
      card.dataset.taskId = t.id;
      card.textContent    = `${t.title} (${t.duration_min}m)`;
      pane.appendChild(card);
    }
  } catch (err) {
    console.error('[tasks] failed to load', err);
  }
}

/* DOMContentLoaded → まずタスクを描画 */
document.addEventListener('DOMContentLoaded', () => {
  loadAndRenderTasks();
  const { undo, redo } = generateUndoRedoHandlers();
  document.getElementById('undo-btn')?.addEventListener('click', undo);
  document.getElementById('redo-btn')?.addEventListener('click', redo);
  updateUndoRedoButtons();
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

    const idx = parseInt(slot.dataset.slotIndex, 10);
    if (slotOccupied(idx)) return;           // safety, should not happen

    e.preventDefault();

    /* move card into new slot */
    slot.appendChild(draggingCard);
    draggingCard.dataset.slotIndex = idx;

    /* update state */
    const tid = draggingCard.dataset.taskId;
    markSlot(idx, tid);
    if (originIndex !== null) unmarkSlot(originIndex);
    pushCommand({
      apply() {
        markSlot(idx, tid);
        if (originIndex !== null) unmarkSlot(originIndex);
      },
      revert() {
        if (originIndex !== null) markSlot(originIndex, tid);
        unmarkSlot(idx);
      },
    });
    saveState();

    /* visual cleanup */
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

})();

/* ---------- minimal fallback impl. ----------------------------------- */
/* 既成ヘルパが無い場合の簡易実装（Map ベース）——重複登録にも強い */
export const gridState = new Map();   // key: slotIndex, value: taskId

export function slotOccupied(i) {
  return gridState.has(i);
}
export function markSlot(i, tid) {
  gridState.set(i, tid);
}
export function unmarkSlot(i) {
  gridState.delete(i);
}

/* ------------------------------------------------------------------
 * Undo / Redo infrastructure (Command Pattern)
 * ---------------------------------------------------------------- */
export const undoStack = [];
export const redoStack = [];
export const HISTORY_LIMIT = 20;

function updateUndoRedoButtons() {
  document.getElementById('undo-btn')?.toggleAttribute('disabled', undoStack.length === 0);
  document.getElementById('redo-btn')?.toggleAttribute('disabled', redoStack.length === 0);
}

export function pushCommand(cmd) {
  undoStack.push(cmd);
  if (undoStack.length > HISTORY_LIMIT) {
    undoStack.shift();
  }
  redoStack.length = 0;
  updateUndoRedoButtons();
}

export function renderGrid() {
  const pane = document.getElementById('task-pane');
  const slots = document.querySelectorAll('[data-slot-index]');
  // reset
  for (const slot of slots) {
    slot.innerHTML = '';
  }
  const cards = new Map();
  pane.querySelectorAll('.task-card').forEach((c) => {
    cards.set(c.dataset.taskId, c);
  });
  for (const [idx, tid] of gridState.entries()) {
    const card = cards.get(tid);
    const slot = document.querySelector(`[data-slot-index="${idx}"]`);
    if (card && slot) {
      slot.appendChild(card);
      card.dataset.slotIndex = idx;
      cards.delete(tid);
    }
  }
  for (const c of cards.values()) {
    c.removeAttribute('data-slot-index');
  }
}

export async function saveState() {
  try {
    const db = await openDb();
    const tx = db.transaction('schedule', 'readwrite');
    const store = tx.objectStore('schedule');
    const data = { date: todayUtcISO(), grid: Array.from(gridState.entries()) };
    store.put(data);
  } catch (err) {
    console.error('saveState failed', err);
  }
}

export function doUndo() {
  const cmd = undoStack.pop();
  if (!cmd) return;
  cmd.revert();
  redoStack.push(cmd);
  renderGrid();
  saveState();
  updateUndoRedoButtons();
}

export function doRedo() {
  const cmd = redoStack.pop();
  if (!cmd) return;
  cmd.apply();
  undoStack.push(cmd);
  renderGrid();
  saveState();
  updateUndoRedoButtons();
}

export function generateUndoRedoHandlers() {
  return { undo: doUndo, redo: doRedo };
}

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && !e.shiftKey && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    doUndo();
  } else if (e.ctrlKey && e.key.toLowerCase() === 'y') {
    e.preventDefault();
    doRedo();
  }
});



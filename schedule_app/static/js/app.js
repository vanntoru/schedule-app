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

  const HISTORY_LIMIT = 20;
  const history = [];
  let historyIndex = -1;

  function pushCommand(cmd) {
    history.splice(historyIndex + 1);
    history.push(cmd);
    if (history.length > HISTORY_LIMIT) {
      history.shift();
    }
    historyIndex = history.length - 1;
    cmd.apply();
  }

  function undo() {
    if (historyIndex < 0) return;
    history[historyIndex].revert();
    historyIndex--;
  }

  function redo() {
    if (historyIndex + 1 >= history.length) return;
    historyIndex++;
    history[historyIndex].apply();
  }

  window.undo = undo;
  window.redo = redo;

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

    const tid = draggingCard.dataset.taskId;
    const prevIndex = originIndex;
    const nextIndex = idx;
    pushCommand({
      apply: () => {
        markSlot(nextIndex, tid);
        if (prevIndex !== null) unmarkSlot(prevIndex);
      },
      revert: () => {
        if (prevIndex !== null) markSlot(prevIndex, tid);
        unmarkSlot(nextIndex);
      },
    });

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

  /* ---------- minimal fallback impl. ----------------------------------- */
  /* 既成ヘルパが無い場合の簡易実装（Map ベース）——重複登録にも強い */
  const gridState = new Map();   // key: slotIndex, value: taskId

  function slotOccupied(i) {
    return gridState.has(i);
  }
  function markSlot(i, tid) {
    gridState.set(i, tid);
    /* TODO: IndexedDB schedule save (phase‑1) */
  }
  function unmarkSlot(i) {
    gridState.delete(i);
  }
})();

// ---------------------------------------------------------------------------
// Schedule grid loading and history (Undo / Redo)
// ---------------------------------------------------------------------------

let scheduleGrid = new Array(144).fill(0); // current grid state

const HISTORY_LIMIT = 20;
const _history = [];
let _ptr = -1; // points to last applied command

/** Render the grid based on `scheduleGrid` values. */
function renderGrid() {
  document.querySelectorAll('.slot[data-slot-index]').forEach((el) => {
    const idx = parseInt(el.dataset.slotIndex, 10);
    const val = scheduleGrid[idx] ?? 0;
    el.classList.remove('bg-gray-200', 'bg-green-200');
    if (val === 1) {
      el.classList.add('bg-gray-200'); // busy
    } else if (val === 2) {
      el.classList.add('bg-green-200'); // task
    }
  });
}

/** Persist the current grid. Placeholder for IndexedDB integration. */
function saveState() {
  // TODO: implement persistence
}

/** Load grid data from the server for the given `date`. */
async function loadGridFromServer(date) {
  const res = await fetch(`/api/schedule/generate?date=${date}`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Schedule API failed: ${res.status}`);
  }
  const data = await res.json();
  scheduleGrid = data.slots.slice();
  renderGrid();
  saveState();
  return scheduleGrid;
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
  if (_history.length > HISTORY_LIMIT) {
    _history.shift();
  } else {
    _ptr++;
  }
}

/** Undo the last command. */
function doUndo() {
  if (_ptr < 0) return;
  const cmd = _history[_ptr];
  _ptr--;
  cmd.revert();
  renderGrid();
  saveState();
}

/** Redo the next command. */
function doRedo() {
  if (_ptr + 1 >= _history.length) return;
  _ptr++;
  const cmd = _history[_ptr];
  cmd.apply();
  renderGrid();
  saveState();
}

/** Generate schedule and record undo information. */
async function generateSchedule(date) {
  const previousGrid = scheduleGrid.slice();
  await loadGridFromServer(date);
  pushCommand({
    apply: () => loadGridFromServer(date),
    revert: () => restoreGrid(previousGrid),
  });
}


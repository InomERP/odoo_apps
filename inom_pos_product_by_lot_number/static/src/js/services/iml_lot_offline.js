/** @odoo-module **/
/**
 * Offline support for the POS Lot/Serial module — Phase 5
 * ─────────────────────────────────────────────────────────────────────
 * Two responsibilities:
 *   1. Persist preloaded lots in IndexedDB so the popup still works
 *      after a hard refresh while offline.
 *   2. Queue lot-creation attempts that happen while offline, and
 *      auto-drain the queue when the connection comes back.
 *
 * Why IndexedDB instead of localStorage?
 *   - Lot counts can be in the thousands; localStorage caps near 5MB
 *     and is synchronous (blocks the UI on writes).
 *   - IndexedDB is async, multi-store, and per-origin sandboxed.
 *
 * This module exports a single class `IMLLotOfflineService` that
 * pos_store.js instantiates once per session.
 */

const DB_NAME = "iml_pos_lot_db";
const DB_VERSION = 1;
const STORE_LOTS = "lots";
const STORE_PENDING = "pending_creates";


/**
 * Minimal Promise wrapper around IndexedDB. No external deps.
 */
class IDB {
    constructor() {
        this._dbPromise = null;
    }

    _openDB() {
        if (this._dbPromise) return this._dbPromise;
        this._dbPromise = new Promise((resolve, reject) => {
            if (typeof indexedDB === "undefined") {
                return reject(new Error("IndexedDB not supported in this browser"));
            }
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onerror = () => reject(req.error);
            req.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
            req.onupgradeneeded = (ev) => {
                const db = ev.target.result;
                if (!db.objectStoreNames.contains(STORE_LOTS)) {
                    db.createObjectStore(STORE_LOTS, { keyPath: "key" });
                }
                if (!db.objectStoreNames.contains(STORE_PENDING)) {
                    db.createObjectStore(STORE_PENDING, { keyPath: "client_id" });
                }
            };
            req.onsuccess = () => resolve(req.result);
        });
        return this._dbPromise;
    }

    async _runTx(storeName, mode, fn) {
        const db = await this._openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction([storeName], mode);
            const store = tx.objectStore(storeName);
            let result;
            const req = fn(store);
            if (req && typeof req.then === "function") {
                req.then(r => (result = r));
            } else if (req && "onsuccess" in req) {
                req.onsuccess = () => (result = req.result);
                req.onerror   = () => reject(req.error);
            }
            tx.oncomplete = () => resolve(result);
            tx.onerror    = () => reject(tx.error);
            tx.onabort    = () => reject(tx.error || new Error("Transaction aborted"));
        });
    }

    put(storeName, record)   { return this._runTx(storeName, "readwrite", s => s.put(record)); }
    delete(storeName, key)   { return this._runTx(storeName, "readwrite", s => s.delete(key)); }
    clear(storeName)         { return this._runTx(storeName, "readwrite", s => s.clear()); }
    get(storeName, key)      { return this._runTx(storeName, "readonly",  s => s.get(key)); }
    getAll(storeName)        { return this._runTx(storeName, "readonly",  s => s.getAll()); }
}


/**
 * The service. Construct with the pos store + an ORM handle.
 */
export class IMLLotOfflineService {
    constructor({ pos, orm }) {
        this.pos = pos;
        this.orm = orm;
        this.idb = new IDB();

        this.isOnline = typeof navigator !== "undefined" ? navigator.onLine : true;
        this._listeners = [];
        this._setupOnlineListeners();
    }

    _setupOnlineListeners() {
        if (typeof window === "undefined") return;
        const onlineHandler = () => {
            this.isOnline = true;
            this._notify({ type: "online" });
            // Auto-drain the queue when we come back
            this.flushPending().catch(err =>
                console.warn("[iml_pos_lot] flushPending failed:", err)
            );
        };
        const offlineHandler = () => {
            this.isOnline = false;
            this._notify({ type: "offline" });
        };
        window.addEventListener("online",  onlineHandler);
        window.addEventListener("offline", offlineHandler);
        this._cleanup = () => {
            window.removeEventListener("online",  onlineHandler);
            window.removeEventListener("offline", offlineHandler);
        };
    }

    onConnectionChange(cb) {
        this._listeners.push(cb);
        return () => {
            this._listeners = this._listeners.filter(l => l !== cb);
        };
    }
    _notify(ev) {
        for (const cb of this._listeners) {
            try { cb(ev); } catch (e) { console.warn(e); }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // LOT CACHE
    // ─────────────────────────────────────────────────────────────────

    async cacheLots(lots) {
        if (!Array.isArray(lots) || !lots.length) return;
        // We key by composite "name|product_id" to allow same lot name
        // across different products (rare but legal in Odoo).
        for (const lot of lots) {
            const productId = lot.product_id?.id ?? lot.product_id;
            if (!lot.name || !productId) continue;
            try {
                await this.idb.put(STORE_LOTS, {
                    key: `${lot.name}|${productId}`,
                    name: lot.name,
                    product_id: productId,
                    product_qty: lot.product_qty ?? 0,
                    expiration_date: lot.expiration_date || false,
                    cached_at: Date.now(),
                });
            } catch (err) {
                console.warn("[iml_pos_lot] cacheLots write failed:", err);
            }
        }
    }

    async getCachedLotsForProduct(productId) {
        try {
            const all = await this.idb.getAll(STORE_LOTS);
            return (all || []).filter(l => l.product_id === productId);
        } catch (err) {
            console.warn("[iml_pos_lot] getCachedLotsForProduct read failed:", err);
            return [];
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PENDING CREATES QUEUE
    // ─────────────────────────────────────────────────────────────────

    async queueLotCreate(vals) {
        const clientId = `iml-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const record = {
            client_id: clientId,
            vals,
            queued_at: new Date().toISOString(),
            tries: 0,
        };
        await this.idb.put(STORE_PENDING, record);
        return record;
    }

    async getPendingCount() {
        const all = await this.idb.getAll(STORE_PENDING);
        return (all || []).length;
    }

    async flushPending() {
        if (!this.isOnline) return { flushed: 0, failed: 0 };

        let batch;
        try {
            batch = await this.idb.getAll(STORE_PENDING);
        } catch (err) {
            console.warn("[iml_pos_lot] flushPending read failed:", err);
            return { flushed: 0, failed: 0 };
        }
        if (!batch || !batch.length) return { flushed: 0, failed: 0 };

        let flushed = 0;
        let failed = 0;
        try {
            const response = await this.orm.call(
                "stock.lot",
                "sync_offline_lot_creates",
                [batch.map(b => ({ client_id: b.client_id, vals: b.vals }))],
            );
            const results = response?.results || [];

            for (const r of results) {
                if (r.ok) {
                    await this.idb.delete(STORE_PENDING, r.client_id);
                    flushed++;
                } else {
                    failed++;
                    // Keep it in queue; bump tries counter
                    const original = batch.find(b => b.client_id === r.client_id);
                    if (original) {
                        original.tries = (original.tries || 0) + 1;
                        original.last_error = r.error;
                        await this.idb.put(STORE_PENDING, original);
                    }
                }
            }
        } catch (err) {
            console.warn("[iml_pos_lot] flushPending RPC failed:", err);
        }
        return { flushed, failed };
    }
}

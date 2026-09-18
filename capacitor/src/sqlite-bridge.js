import { Capacitor } from '@capacitor/core';
import { CapacitorSQLite, SQLiteConnection } from '@capacitor-community/sqlite';

class IndexedFallback {
  constructor(){ this.dbp = null; }
  open(){
    if (this.dbp) return this.dbp;
    this.dbp = new Promise((resolve,reject)=>{
      const req=indexedDB.open('oraforge_pos_fallback',1);
      req.onupgradeneeded=()=>{ const db=req.result; if(!db.objectStoreNames.contains('kv')) db.createObjectStore('kv'); };
      req.onsuccess=()=>resolve(req.result); req.onerror=()=>reject(req.error);
    });
    return this.dbp;
  }
  async get(key,fallback){ const db=await this.open(); return new Promise((resolve,reject)=>{ const tx=db.transaction('kv','readonly'); const r=tx.objectStore('kv').get(key); r.onsuccess=()=>resolve(r.result===undefined?fallback:r.result); r.onerror=()=>reject(r.error); }); }
  async set(key,value){ const db=await this.open(); return new Promise((resolve,reject)=>{ const tx=db.transaction('kv','readwrite'); tx.objectStore('kv').put(value,key); tx.oncomplete=()=>resolve(); tx.onerror=()=>reject(tx.error); }); }
}

class OraforgeDB {
  constructor(){ this.sqlite=null; this.db=null; this.fallback=new IndexedFallback(); this.native=false; }
  async init(){
    this.native = ['android','ios'].includes(Capacitor.getPlatform());
    if (!this.native) return this;
    try {
      this.sqlite = new SQLiteConnection(CapacitorSQLite);
      try { this.db = await this.sqlite.createConnection('oraforge_pos', false, 'no-encryption', 1, false); }
      catch (_) { this.db = await this.sqlite.retrieveConnection('oraforge_pos', false); }
      await this.db.open();
      await this.db.execute('CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);');
    } catch (err) {
      console.error('Native SQLite unavailable; using IndexedDB fallback', err);
      this.native = false; this.db = null;
    }
    return this;
  }
  async get(key,fallback){
    if (!this.native || !this.db) return this.fallback.get(key,fallback);
    const r = await this.db.query('SELECT value FROM kv_store WHERE key = ? LIMIT 1;', [key]);
    if (!r.values || !r.values.length) return fallback;
    try { return JSON.parse(r.values[0].value); } catch (_) { return fallback; }
  }
  async set(key,value){
    if (!this.native || !this.db) return this.fallback.set(key,value);
    await this.db.run('INSERT OR REPLACE INTO kv_store(key,value) VALUES (?,?);', [key, JSON.stringify(value)]);
  }
}

window.OraforgeDB = new OraforgeDB();
window.OraforgeDBReady = window.OraforgeDB.init();

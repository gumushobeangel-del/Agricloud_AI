import type { Farm, HarvestRecord, Recommendation, User } from "./api";

export type CachedCrop = { id: number; name: string; local_names: string; category: string; guidance_notes: string; source_title: string; source_url: string; verified: boolean; active: boolean };
export type CachedWorkspace = { user: User; farms: Farm[]; crops: CachedCrop[]; recommendations: Recommendation[]; harvests: HarvestRecord[]; savedAt: number };
export type PendingHarvest = { id: string; user_id: number; client_key: string; farm: number; crop: string; harvest_date: string; quantity_kg: string; queued_at: number; issue?: string };

const DB_NAME = "agricloud-farmer-cache";
const DB_VERSION = 1;
function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!("indexedDB" in window)) { reject(new Error("Offline storage is not supported on this device.")); return; }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("workspaces")) db.createObjectStore("workspaces", { keyPath: "userId" });
      if (!db.objectStoreNames.contains("pendingHarvests")) db.createObjectStore("pendingHarvests", { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open offline storage."));
  });
}

export async function saveWorkspace(snapshot: CachedWorkspace) {
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("workspaces", "readwrite");
    transaction.objectStore("workspaces").put({ ...snapshot, userId: snapshot.user.id });
    transaction.oncomplete = () => resolve(); transaction.onerror = () => reject(transaction.error); transaction.onabort = () => reject(transaction.error);
  });
  db.close();
}

export async function getWorkspace(userId: number): Promise<CachedWorkspace | null> {
  const db = await openDatabase();
  const saved = await new Promise<(CachedWorkspace & { userId: number }) | undefined>((resolve, reject) => {
    const request = db.transaction("workspaces").objectStore("workspaces").get(userId);
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
  db.close();
  if (!saved) return null;
  const { userId: _key, ...snapshot } = saved;
  return snapshot;
}

export async function queueHarvest(userId: number, item: Omit<PendingHarvest, "id" | "user_id" | "queued_at">) {
  const pending: PendingHarvest = { ...item, id: `${userId}:${item.client_key}`, user_id: userId, queued_at: Date.now() };
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("pendingHarvests", "readwrite");
    transaction.objectStore("pendingHarvests").put(pending);
    transaction.oncomplete = () => resolve(); transaction.onerror = () => reject(transaction.error);
  });
  db.close();
  return pending;
}

export async function getPendingHarvests(userId: number): Promise<PendingHarvest[]> {
  const db = await openDatabase();
  const all = await new Promise<PendingHarvest[]>((resolve, reject) => {
    const request = db.transaction("pendingHarvests").objectStore("pendingHarvests").getAll();
    request.onsuccess = () => resolve((request.result as PendingHarvest[]).filter((item) => item.user_id === userId));
    request.onerror = () => reject(request.error);
  });
  db.close();
  return all;
}

export async function removePendingHarvest(id: string) {
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("pendingHarvests", "readwrite");
    transaction.objectStore("pendingHarvests").delete(id);
    transaction.oncomplete = () => resolve(); transaction.onerror = () => reject(transaction.error);
  });
  db.close();
}

export async function flagPendingHarvest(id: string, issue: string) {
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const store = db.transaction("pendingHarvests", "readwrite").objectStore("pendingHarvests");
    const request = store.get(id);
    request.onsuccess = () => { if (request.result) store.put({ ...request.result, issue }); };
    request.onerror = () => reject(request.error);
    request.transaction!.oncomplete = () => resolve(); request.transaction!.onerror = () => reject(request.transaction!.error);
  });
  db.close();
}

export async function clearWorkspace(userId: number) {
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    // Keep the signed-in user's queued changes across sign-out so a brief
    // disconnect cannot silently erase a harvest waiting to sync. Queue items
    // are scoped by user ID and will only sync after that same user signs in.
    const transaction = db.transaction("workspaces", "readwrite");
    transaction.objectStore("workspaces").delete(userId);
    transaction.oncomplete = () => resolve(); transaction.onerror = () => reject(transaction.error);
  });
  db.close();
}

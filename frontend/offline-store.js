class OfflineStore {
    constructor(dbName = 'nextgen-tutor-db', version = 1) {
        this.dbName = dbName;
        this.version = version;
        this.db = null;
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains('lessons'))
                    db.createObjectStore('lessons', { keyPath: 'id' });
                if (!db.objectStoreNames.contains('knowledge-graph'))
                    db.createObjectStore('knowledge-graph', { keyPath: 'subject' });
                if (!db.objectStoreNames.contains('progress'))
                    db.createObjectStore('progress', { keyPath: 'key' });
                if (!db.objectStoreNames.contains('pending-actions'))
                    db.createObjectStore('pending-actions', { keyPath: 'id', autoIncrement: true });
                if (!db.objectStoreNames.contains('user-profile'))
                    db.createObjectStore('user-profile', { keyPath: 'id' });
            };
            request.onsuccess = (e) => {
                this.db = e.target.result;
                resolve(this.db);
            };
            request.onerror = () => reject(request.error);
        });
    }

    async put(storeName, data) {
        if (!this.db) await this.init();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            tx.objectStore(storeName).put(data);
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async get(storeName, key) {
        if (!this.db) await this.init();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const request = tx.objectStore(storeName).get(key);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getAll(storeName) {
        if (!this.db) await this.init();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const request = tx.objectStore(storeName).getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async delete(storeName, key) {
        if (!this.db) await this.init();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            tx.objectStore(storeName).delete(key);
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async clear(storeName) {
        if (!this.db) await this.init();
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            tx.objectStore(storeName).clear();
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async addPendingAction(action) {
        action.timestamp = Date.now();
        await this.put('pending-actions', action);
    }

    async getPendingActions() {
        return this.getAll('pending-actions');
    }

    async clearPendingActions() {
        await this.clear('pending-actions');
    }

    async syncPendingActions(apiCall) {
        const actions = await this.getPendingActions();
        let synced = 0;
        for (const action of actions) {
            try {
                await apiCall(action.endpoint, action.method, action.body);
                await this.delete('pending-actions', action.id);
                synced++;
            } catch (e) {
                console.warn('Sync failed for action:', action, e);
            }
        }
        return synced;
    }

    async cacheKnowledgeGraph(subject, data) {
        await this.put('knowledge-graph', { subject, data, cachedAt: Date.now() });
    }

    async getCachedKnowledgeGraph(subject) {
        const cached = await this.get('knowledge-graph', subject);
        if (cached && Date.now() - cached.cachedAt < 3600000) return cached.data;
        return null;
    }

    async cacheUserProfile(profile) {
        await this.put('user-profile', { id: 'current', ...profile, cachedAt: Date.now() });
    }

    async getCachedUserProfile() {
        const cached = await this.get('user-profile', 'current');
        if (cached) return cached;
        return null;
    }
}

if (typeof window !== 'undefined') {
    window.OfflineStore = OfflineStore;
}

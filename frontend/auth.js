// Sign-in state shared by the account page and the parent dashboard.
// Keys start with "nt_" so the learning page's per-child storage leaves them alone.
const NT = {
    API: '/api/v1',

    get access() { return localStorage.getItem('nt_access'); },
    get refresh() { return localStorage.getItem('nt_refresh'); },
    get email() { return localStorage.getItem('nt_email'); },
    get signedIn() { return !!this.refresh; },

    saveParent(tokens) {
        localStorage.setItem('nt_access', tokens.access_token);
        localStorage.setItem('nt_refresh', tokens.refresh_token);
        localStorage.setItem('nt_email', tokens.email);
    },

    saveChild(session) {
        localStorage.setItem('nt_child_token', session.access_token);
        localStorage.setItem('nt_child', JSON.stringify(session.child));
    },

    clearChild() {
        localStorage.removeItem('nt_child_token');
        localStorage.removeItem('nt_child');
    },

    signOut() {
        ['nt_access', 'nt_refresh', 'nt_email'].forEach(k => localStorage.removeItem(k));
        this.clearChild();
        sessionStorage.removeItem('nt_grownup');
    },

    // Plain request with no sign-in, for login and register.
    async post(path, body) {
        const res = await fetch(this.API + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    },

    async _renew() {
        if (!this.refresh) return false;
        const r = await this.post('/auth/refresh', { refresh_token: this.refresh });
        if (!r.ok) return false;
        this.saveParent(r.data);
        return true;
    },

    // Request as the signed-in parent. Renews the short-lived token once if needed.
    async parent(path, method = 'GET', body = null) {
        const send = () => fetch(this.API + path, {
            method,
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + this.access },
            body: body ? JSON.stringify(body) : undefined,
        });
        let res = this.access ? await send() : { status: 401 };
        if (res.status === 401 && await this._renew()) res = await send();
        if (res.status === 401) { this.signOut(); return { ok: false, status: 401, data: {} }; }
        return { ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) };
    },

    // Grown-up check: the parent's password, remembered for this browser tab only.
    get grownUp() { return sessionStorage.getItem('nt_grownup') === '1'; },

    async confirmGrownUp(password) {
        const r = await this.post('/auth/login', { email: this.email, password });
        if (r.ok) { this.saveParent(r.data); sessionStorage.setItem('nt_grownup', '1'); }
        return r.ok;
    },

    // Turns the API's error shapes into one readable line.
    message(data, fallback) {
        const d = data && (data.error || data.detail);
        if (typeof d === 'string') return d;
        if (Array.isArray(d) && d[0] && d[0].msg) return d[0].msg.replace(/^Value error, /, '');
        return fallback;
    },
};

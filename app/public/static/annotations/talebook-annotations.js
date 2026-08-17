const COLORS = ['#f6c85f', '#ef8a62', '#8ecae6', '#a7c957', '#cdb4db'];
const SELECTION_ACTIONS = [
    { id: 'copy', icon: '▣', label: '复制' },
    { id: 'note', icon: '✦', label: '想法' },
    { id: 'highlight', icon: 'A', label: '划线' },
];

function escapeHtml(value = '') {
    return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

export function annotationSearchQueries(annotation) {
    const quote = String(annotation?.quote || '').trim();
    if (!quote) return [];
    const normalized = quote.replace(/\s+/g, ' ');
    const compact = quote.replace(/\s+/g, '');
    const candidates = [quote, normalized];
    if (compact !== normalized && /[\u3400-\u9fff]/.test(compact)) candidates.push(compact);
    for (const text of [normalized, compact]) {
        if (text.length > 80) {
            candidates.push(text.slice(0, 80));
            candidates.push(text.slice(Math.max(0, Math.floor((text.length - 80) / 2)), Math.floor((text.length - 80) / 2) + 80));
            candidates.push(text.slice(-80));
        }
    }
    return [...new Set(candidates.map(value => value.trim()).filter(value => (
        /[\u3400-\u9fff]/.test(value) ? value.length >= 4 : value.length >= 8
    )))];
}

export class TalebookAnnotations {
    constructor(options) {
        this.options = options;
        this.bookId = Number(options.bookId);
        this.format = options.format;
        this.items = [];
        this.selection = null;
        this.selectionRect = null;
        this.color = COLORS[0];
        this.annotationTargets = new WeakMap();
        this.hoverHideTimer = null;
        this.mount();
        this.bindSelectionToolbar();
        this.load().then(() => this.openTarget());
    }

    async request(path, options = {}) {
        if (this.options.request) return this.options.request(path, options);
        const response = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...options });
        const data = await response.json();
        if (data.err !== 'ok') throw new Error(data.msg || '操作失败');
        return data;
    }

    mount() {
        this.trigger = document.createElement('button');
        this.trigger.className = 'ta-trigger';
        this.trigger.textContent = '批注';
        this.panel = document.createElement('aside');
        this.panel.className = 'ta-panel';
        this.panel.setAttribute('aria-label', '阅读批注');
        this.panel.innerHTML = `<header class="ta-head"><div class="ta-head-row"><h2 class="ta-title">阅读批注</h2><button class="ta-close" aria-label="关闭">×</button></div><div class="ta-actions"><button class="ta-button ta-primary" data-action="selection">标记选中文字</button><button class="ta-button" data-action="note">记录当前位置</button></div><div class="ta-status"></div></header><div class="ta-editor" hidden></div><div class="ta-list"></div>`;
        this.selectionToolbar = document.createElement('div');
        this.selectionToolbar.className = 'ta-selection-toolbar';
        this.selectionToolbar.hidden = true;
        this.selectionToolbar.setAttribute('role', 'toolbar');
        this.selectionToolbar.setAttribute('aria-label', '选中文字操作');
        this.selectionToolbar.innerHTML = `<div class="ta-selection-actions">${SELECTION_ACTIONS.map(action => `<button class="ta-selection-action" data-selection-action="${action.id}"><span class="ta-action-icon" aria-hidden="true">${action.icon}</span><span class="ta-action-label">${action.label}</span></button>`).join('')}</div><section class="ta-inline-composer" aria-label="写想法" hidden><div class="ta-inline-head"><strong class="ta-inline-title">写想法</strong><button class="ta-inline-close" type="button" aria-label="关闭想法输入">×</button></div><blockquote class="ta-inline-quote"></blockquote><textarea maxlength="500" placeholder="记录一下此刻想法…"></textarea><div class="ta-inline-foot"><span class="ta-inline-count">0/500</span><button class="ta-inline-cancel" type="button">取消</button><button class="ta-inline-save" type="button" disabled>添加想法</button></div><div class="ta-inline-status" role="status"></div></section>`;
        this.annotationPeek = document.createElement('button');
        this.annotationPeek.className = 'ta-annotation-peek';
        this.annotationPeek.hidden = true;
        this.annotationPeek.type = 'button';
        this.annotationPeek.setAttribute('aria-label', '查看想法');
        this.annotationPeek.innerHTML = '<span aria-hidden="true">✦</span><span>想法</span>';
        document.body.append(this.trigger, this.panel, this.selectionToolbar, this.annotationPeek);
        this.trigger.addEventListener('click', () => this.toggle(true));
        this.panel.querySelector('.ta-close').addEventListener('click', () => this.toggle(false));
        this.panel.querySelector('[data-action="selection"]').addEventListener('click', () => this.start('highlight'));
        this.panel.querySelector('[data-action="note"]').addEventListener('click', () => this.start('note'));
        this.panel.querySelector('.ta-list').addEventListener('click', event => this.onListClick(event));
        this.selectionToolbar.querySelector('.ta-selection-actions').addEventListener('click', event => {
            const button = event.target.closest('[data-selection-action]');
            if (button) this.handleSelectionAction(button.dataset.selectionAction);
        });
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        composer.querySelector('textarea').addEventListener('input', event => this.updateThoughtCount(event.target.value));
        composer.querySelector('.ta-inline-save').addEventListener('click', () => this.saveThought());
        composer.querySelector('.ta-inline-cancel').addEventListener('click', () => this.closeThoughtComposer());
        composer.querySelector('.ta-inline-close').addEventListener('click', () => this.closeThoughtComposer());
        this.annotationPeek.addEventListener('pointerenter', () => this.cancelAnnotationPeekHide());
        this.annotationPeek.addEventListener('pointerleave', () => this.hideAnnotationPeekSoon());
        this.annotationPeek.addEventListener('click', () => this.openAnnotation(this.peekItem));
    }

    bindSelectionToolbar() {
        document.addEventListener('mouseup', event => {
            if (this.panel.contains(event.target) || this.selectionToolbar.contains(event.target)) return;
            window.setTimeout(() => this.captureSelection(), 0);
        });
        window.addEventListener('talebook-reader-selection', event => this.captureSelection(event.detail));
        window.addEventListener('talebook-reader-selection-cleared', () => {
            if (!this.isThoughtComposerOpen()) this.hideSelectionToolbar();
        });
        document.addEventListener('selectionchange', () => {
            window.setTimeout(() => this.dismissToolbarForCollapsedSelection(), 0);
        });
        document.addEventListener('mousedown', event => {
            if (!this.selectionToolbar.contains(event.target)) this.hideSelectionToolbar();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') this.hideSelectionToolbar();
        });
    }

    isThoughtComposerOpen() {
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        return Boolean(composer && !composer.hidden);
    }

    async dismissToolbarForCollapsedSelection() {
        if (this.selectionToolbar.hidden || this.isThoughtComposerOpen()) return;
        const selection = this.options.getSelection ? await this.options.getSelection() : null;
        if (!selection?.quote) this.hideSelectionToolbar();
    }

    async captureSelection(position = null) {
        const selection = this.options.getSelection ? await this.options.getSelection() : null;
        if (!selection?.quote) { this.hideSelectionToolbar(); return; }
        this.selection = { ...selection };
        const native = window.getSelection();
        const rect = position || (!native?.isCollapsed && native.rangeCount ? native.getRangeAt(0).getBoundingClientRect() : null);
        if (!rect) return;
        this.selectionRect = rect;
        this.closeThoughtComposer();
        this.positionSelectionToolbar(false);
        this.selectionToolbar.hidden = false;
    }

    positionSelectionToolbar(expanded) {
        const rect = this.selectionRect;
        if (!rect) return;
        const halfWidth = expanded ? 190 : 102;
        const left = Math.min(window.innerWidth - halfWidth, Math.max(halfWidth, rect.left + (rect.width || 0) / 2));
        const useBottom = rect.top < (expanded ? 310 : 90);
        this.selectionToolbar.dataset.placement = useBottom ? 'bottom' : 'top';
        this.selectionToolbar.style.left = `${left}px`;
        this.selectionToolbar.style.top = `${useBottom ? rect.top + (rect.height || 0) + 10 : rect.top - 10}px`;
    }

    hideSelectionToolbar() {
        this.selectionToolbar.hidden = true;
        this.closeThoughtComposer();
    }

    bindAnnotationTarget(target, item, frame = null) {
        if (!target || !item?.content || this.annotationTargets.get(target) === item.id) return;
        this.annotationTargets.set(target, item.id);
        target.classList.add('ta-annotation-target');
        target.dataset.taAnnotationId = String(item.id);
        target.addEventListener('pointerenter', () => {
            const rect = target.getBoundingClientRect();
            const frameRect = frame?.getBoundingClientRect ? frame.getBoundingClientRect() : null;
            this.showAnnotationPeek(item, {
                left: rect.left + (frameRect?.left || 0),
                top: rect.top + (frameRect?.top || 0),
                width: rect.width,
                height: rect.height,
            });
        });
        target.addEventListener('pointerleave', () => this.hideAnnotationPeekSoon());
    }

    showAnnotationPeek(item, rect) {
        if (!item || !rect) return;
        this.cancelAnnotationPeekHide();
        this.peekItem = item;
        const left = Math.min(window.innerWidth - 54, Math.max(54, rect.left + rect.width / 2));
        this.annotationPeek.style.left = `${left}px`;
        this.annotationPeek.style.top = `${Math.max(10, rect.top - 8)}px`;
        this.annotationPeek.hidden = false;
    }

    cancelAnnotationPeekHide() {
        if (this.hoverHideTimer) window.clearTimeout(this.hoverHideTimer);
        this.hoverHideTimer = null;
    }

    hideAnnotationPeekSoon() {
        this.cancelAnnotationPeekHide();
        this.hoverHideTimer = window.setTimeout(() => { this.annotationPeek.hidden = true; }, 140);
    }

    openAnnotation(item) {
        if (!item) return;
        this.annotationPeek.hidden = true;
        this.toggle(true);
        const card = this.panel.querySelector(`[data-id="${item.id}"]`);
        if (!card) return;
        card.classList.add('ta-card-active');
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        window.setTimeout(() => card.classList.remove('ta-card-active'), 1800);
    }

    async handleSelectionAction(action) {
        if (!this.selection?.quote) return;
        if (action === 'copy') await this.copySelection();
        else if (action === 'note') this.showThoughtComposer();
        else if (action === 'highlight') await this.saveHighlight();
    }

    async copySelection() {
        try {
            if (this.options.copyText) await this.options.copyText(this.selection.quote);
            else await navigator.clipboard.writeText(this.selection.quote);
            this.hideSelectionToolbar();
            this.toast('已复制');
        } catch (error) {
            this.inlineStatus('复制失败，请使用系统复制');
        }
    }

    showThoughtComposer() {
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        const textarea = composer.querySelector('textarea');
        composer.hidden = false;
        composer.querySelector('.ta-inline-quote').textContent = this.selection.quote;
        textarea.value = '';
        this.updateThoughtCount('');
        this.inlineStatus('');
        this.positionSelectionToolbar(true);
        textarea.focus();
    }

    closeThoughtComposer() {
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        if (composer) composer.hidden = true;
        if (this.selectionRect) this.positionSelectionToolbar(false);
    }

    updateThoughtCount(value) {
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        composer.querySelector('.ta-inline-count').textContent = `${value.length}/500`;
        composer.querySelector('.ta-inline-save').disabled = !value.trim();
    }

    inlineStatus(message) {
        this.selectionToolbar.querySelector('.ta-inline-status').textContent = message || '';
    }

    async saveThought() {
        const composer = this.selectionToolbar.querySelector('.ta-inline-composer');
        const content = composer.querySelector('textarea').value.trim();
        if (!content) return;
        composer.querySelector('.ta-inline-save').disabled = true;
        try {
            await this.persistSelection('note', content);
            this.hideSelectionToolbar();
            this.toast('想法已保存');
        } catch (error) {
            this.inlineStatus(error.message);
            composer.querySelector('.ta-inline-save').disabled = false;
        }
    }

    async saveHighlight() {
        try {
            const annotation = await this.persistSelection('highlight', '');
            await this.options.locate?.(annotation);
            this.hideSelectionToolbar();
            this.toast('已划线');
        } catch (error) { this.inlineStatus(error.message); }
    }

    async persistSelection(kind, content) {
        const source = this.selection;
        const prefix = String(source.prefix || '').slice(-500);
        const suffix = String(source.suffix || '').slice(0, 500);
        const body = { client_id: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, kind, format: this.format, quote: source.quote || '', prefix, suffix, chapter: source.chapter || '', locator: source.locator || {}, content, color: this.color };
        const data = await this.request(`/api/book/${this.bookId}/annotations`, { method: 'POST', body: JSON.stringify(body) });
        await this.load();
        return data.annotation;
    }

    toast(message) {
        const toast = document.createElement('div');
        toast.className = 'ta-selection-toast';
        toast.textContent = message;
        document.body.append(toast);
        window.setTimeout(() => toast.remove(), 1600);
    }

    toggle(open) { this.panel.classList.toggle('ta-open', open); }
    status(message) { this.panel.querySelector('.ta-status').textContent = message || ''; }

    async load() {
        try {
            const data = await this.request(`/api/book/${this.bookId}/annotations`);
            this.items = data.annotations || [];
            this.render();
            if (this.options.onAnnotations) this.options.onAnnotations(this.items);
        } catch (error) { this.status(error.message); }
    }

    render() {
        const list = this.panel.querySelector('.ta-list');
        if (!this.items.length) {
            list.innerHTML = '<div class="ta-empty">还没有批注。<br>选择一段文字，或记录当前页。</div>';
            return;
        }
        list.innerHTML = this.items.map(item => `<article class="ta-card" data-id="${item.id}" style="--mark:${item.color}"><div class="ta-meta"><span>${escapeHtml(item.chapter || '当前位置')}</span><time>${escapeHtml((item.update_time || '').slice(0, 10))}</time></div>${item.quote ? `<p class="ta-quote">“${escapeHtml(item.quote)}”</p>` : ''}${item.content ? `<p class="ta-note">${escapeHtml(item.content)}</p>` : ''}<div class="ta-card-tools"><button class="ta-link" data-edit="${item.id}">编辑</button><button class="ta-link" data-delete="${item.id}">删除</button></div></article>`).join('');
    }

    async start(kind) {
        const getLocation = kind === 'highlight' ? this.options.getSelection : this.options.getLocation;
        this.selection = getLocation ? await getLocation() : null;
        if (!this.selection || (kind === 'highlight' && !this.selection.quote)) {
            this.status(kind === 'highlight' ? '请先在正文中选择一段文字' : '暂时无法读取当前位置');
            return;
        }
        this.selection.kind = kind;
        this.showEditor();
    }

    showEditor(item = null) {
        const editor = this.panel.querySelector('.ta-editor');
        this.color = item?.color || this.color;
        editor.hidden = false;
        editor.innerHTML = `<textarea maxlength="20000" placeholder="写下你的想法（可选）">${escapeHtml(item?.content || '')}</textarea><div class="ta-colors">${COLORS.map(color => `<button class="ta-color ${color === this.color ? 'ta-selected' : ''}" data-color="${color}" style="background:${color}" aria-label="颜色 ${color}"></button>`).join('')}</div><div class="ta-actions"><button class="ta-button ta-primary" data-save>保存</button><button class="ta-button" data-cancel>取消</button></div>`;
        editor.querySelectorAll('[data-color]').forEach(button => button.addEventListener('click', () => {
            this.color = button.dataset.color;
            editor.querySelectorAll('[data-color]').forEach(node => node.classList.toggle('ta-selected', node === button));
        }));
        editor.querySelector('[data-cancel]').addEventListener('click', () => { editor.hidden = true; });
        editor.querySelector('[data-save]').addEventListener('click', () => item ? this.update(item, editor) : this.create(editor));
    }

    async create(editor) {
        try {
            await this.persistSelection(this.selection.kind, editor.querySelector('textarea').value);
            editor.hidden = true; this.status('已保存');
        } catch (error) { this.status(error.message); }
    }

    async update(item, editor) {
        try {
            await this.request(`/api/book/${this.bookId}/annotations/${item.id}`, { method: 'PUT', body: JSON.stringify({ content: editor.querySelector('textarea').value, color: this.color }) });
            editor.hidden = true; this.status('已更新'); await this.load();
        } catch (error) { this.status(error.message); }
    }

    async onListClick(event) {
        const edit = event.target.closest('[data-edit]');
        const remove = event.target.closest('[data-delete]');
        const card = event.target.closest('[data-id]');
        if (!card) return;
        const item = this.items.find(row => row.id === Number(card.dataset.id));
        if (edit) return this.showEditor(item);
        if (remove) {
            if (!window.confirm('删除这条批注？')) return;
            await this.request(`/api/book/${this.bookId}/annotations/${item.id}`, { method: 'DELETE' });
            await this.load(); return;
        }
        if (this.options.locate) {
            const result = await this.options.locate(item);
            this.status(result === 'approximate' ? '原位置已变化，已按原文近似定位' : result === 'failed' ? '未找到原文位置' : '已定位');
        }
    }

    async openTarget() {
        const id = Number(new URLSearchParams(location.search).get('annotation'));
        if (!id) return;
        const item = this.items.find(row => row.id === id);
        if (item) { this.toggle(true); await this.options.locate?.(item); }
    }
}

window.TalebookAnnotations = TalebookAnnotations;

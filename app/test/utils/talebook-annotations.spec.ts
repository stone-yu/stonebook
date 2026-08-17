import { afterEach, describe, expect, it, vi } from 'vitest';
import { annotationSearchQueries, TalebookAnnotations } from '../../public/static/annotations/talebook-annotations.js';

const response = (body: object) => Promise.resolve({ json: () => Promise.resolve(body) });

afterEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    history.replaceState({}, '', '/read/7');
});

describe('TalebookAnnotations', () => {
    it('builds stable fallback queries for annotations imported from another format', () => {
        const quote = `${'这是 PDF 转换后带有 空白差异的原文。'.repeat(8)}结尾`;
        const queries = annotationSearchQueries({ quote });

        expect(queries[0]).toBe(quote);
        expect(queries).toContain(quote.replace(/\s+/g, ''));
        expect(queries.some(item => item.length === 80)).toBe(true);
        expect(annotationSearchQueries({ quote: '短句' })).toEqual([]);
        expect(annotationSearchQueries({ quote: '功颂德碑' })).toEqual(['功颂德碑']);
    });

    it('loads the private book list and creates a selected-text highlight', async () => {
        const fetch = vi.spyOn(globalThis, 'fetch')
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotation: { id: 1 } }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [{ id: 1, quote: '原文', content: '笔记', locator: {}, color: '#f6c85f' }] }) as never);
        const annotations = new TalebookAnnotations({
            bookId: 7,
            format: 'epub',
            getSelection: () => ({ quote: '原文', chapter: '第一章', locator: { cfi: 'epubcfi(/6/2)' } }),
        });
        await vi.waitFor(() => expect(document.querySelector('.ta-empty')).not.toBeNull());

        await annotations.start('highlight');
        const editor = document.querySelector('.ta-editor') as HTMLElement;
        (editor.querySelector('textarea') as HTMLTextAreaElement).value = '笔记';
        (editor.querySelector('[data-save]') as HTMLButtonElement).click();

        await vi.waitFor(() => expect(document.querySelector('.ta-card')?.textContent).toContain('原文'));
        expect(fetch.mock.calls[1][0]).toBe('/api/book/7/annotations');
        expect(JSON.parse(fetch.mock.calls[1][1]?.body as string)).toMatchObject({ kind: 'highlight', format: 'epub', quote: '原文' });
    });

    it('opens and locates a deep-linked annotation', async () => {
        history.replaceState({}, '', '/read/7?annotation=9');
        vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({
            err: 'ok',
            annotations: [{ id: 9, quote: '目标', content: '', locator: { page: 2 }, color: '#8ecae6' }],
        }) as never);
        const locate = vi.fn().mockResolvedValue('exact');
        new TalebookAnnotations({ bookId: 7, format: 'pdf', locate });

        await vi.waitFor(() => expect(locate).toHaveBeenCalled());
        expect(document.querySelector('.ta-panel')?.classList.contains('ta-open')).toBe(true);
    });

    it('shows copy, thought and highlight actions and edits the thought in place', async () => {
        const fetch = vi.spyOn(globalThis, 'fetch')
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotation: { id: 2 } }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never);
        const annotations = new TalebookAnnotations({
            bookId: 7,
            format: 'txt',
            getSelection: () => ({ quote: '选中的原文', chapter: '第二章', locator: { chapter_index: 1 } }),
        });
        await annotations.captureSelection({ left: 100, top: 120, width: 80 });

        const toolbar = document.querySelector('.ta-selection-toolbar') as HTMLElement;
        expect(toolbar.hidden).toBe(false);
        expect(toolbar.textContent).toContain('复制');
        expect(toolbar.textContent).toContain('想法');
        expect(toolbar.textContent).toContain('划线');
        (toolbar.querySelector('[data-selection-action="note"]') as HTMLButtonElement).click();
        const composer = toolbar.querySelector('.ta-inline-composer') as HTMLElement;
        expect(composer.hidden).toBe(false);
        expect(composer.textContent).toContain('选中的原文');
        const textarea = composer.querySelector('textarea') as HTMLTextAreaElement;
        textarea.value = '这里很重要';
        textarea.dispatchEvent(new Event('input'));
        expect(composer.querySelector('.ta-inline-count')?.textContent).toBe('5/500');
        (composer.querySelector('.ta-inline-save') as HTMLButtonElement).click();
        await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
        expect(JSON.parse(fetch.mock.calls[1][1]?.body as string)).toMatchObject({ kind: 'note', content: '这里很重要', quote: '选中的原文' });
    });

    it('copies without saving and saves a highlight immediately', async () => {
        const fetch = vi.spyOn(globalThis, 'fetch')
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotation: { id: 3 } }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never);
        const copyText = vi.fn().mockResolvedValue(undefined);
        const locate = vi.fn().mockResolvedValue('exact');
        const annotations = new TalebookAnnotations({
            bookId: 7,
            format: 'pdf',
            copyText,
            locate,
            getSelection: () => ({ quote: '复制或划线', chapter: '第 3 页', locator: { page: 3 } }),
        });
        await annotations.captureSelection({ left: 100, top: 400, width: 80 });
        await annotations.handleSelectionAction('copy');
        expect(copyText).toHaveBeenCalledWith('复制或划线');
        expect(fetch).toHaveBeenCalledTimes(1);

        await annotations.captureSelection({ left: 100, top: 400, width: 80 });
        await annotations.handleSelectionAction('highlight');
        await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
        expect(JSON.parse(fetch.mock.calls[1][1]?.body as string)).toMatchObject({ kind: 'highlight', content: '', quote: '复制或划线' });
        expect(locate).toHaveBeenCalledWith({ id: 3 });
    });

    it('trims malformed reader context before saving a thought', async () => {
        const fetch = vi.spyOn(globalThis, 'fetch')
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotation: { id: 4 } }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [] }) as never);
        const annotations = new TalebookAnnotations({ bookId: 7, format: 'epub' });
        annotations.selection = { quote: '原文', prefix: `开头${'前'.repeat(700)}`, suffix: `${'后'.repeat(700)}结尾`, locator: {} };

        await annotations.persistSelection('note', '想法');

        const body = JSON.parse(fetch.mock.calls[1][1]?.body as string);
        expect(body.prefix).toHaveLength(500);
        expect(body.prefix).not.toContain('开头');
        expect(body.suffix).toHaveLength(500);
        expect(body.suffix).not.toContain('结尾');
    });

    it('dismisses the selection toolbar when the selection collapses but keeps an open thought editor', async () => {
        vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({ err: 'ok', annotations: [] }) as never);
        let selected = { quote: '仍然选中', locator: {} };
        const annotations = new TalebookAnnotations({ bookId: 7, format: 'txt', getSelection: () => selected });
        await annotations.captureSelection({ left: 40, top: 100, width: 80 });
        const toolbar = document.querySelector('.ta-selection-toolbar') as HTMLElement;

        selected = null as never;
        document.dispatchEvent(new Event('selectionchange'));
        await vi.waitFor(() => expect(toolbar.hidden).toBe(true));

        selected = { quote: '输入中的原文', locator: {} };
        await annotations.captureSelection({ left: 40, top: 100, width: 80 });
        annotations.showThoughtComposer();
        selected = null as never;
        document.dispatchEvent(new Event('selectionchange'));
        await new Promise(resolve => setTimeout(resolve, 10));
        expect(toolbar.hidden).toBe(false);
    });

    it('shows thought content on hover and enters editing only from the edit button', async () => {
        const item = { id: 12, kind: 'note', quote: '有想法的原文', content: '我的想法', locator: {}, color: '#f6c85f' };
        vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({ err: 'ok', annotations: [item] }) as never);
        const annotations = new TalebookAnnotations({ bookId: 7, format: 'txt' });
        await vi.waitFor(() => expect(document.querySelector('[data-id="12"]')).not.toBeNull());
        const target = document.createElement('span');
        target.textContent = item.quote;
        target.getBoundingClientRect = () => ({ left: 80, top: 160, width: 120, height: 24, right: 200, bottom: 184, x: 80, y: 160, toJSON: () => ({}) });
        document.body.append(target);
        HTMLElement.prototype.scrollIntoView = vi.fn();

        annotations.bindAnnotationTarget(target, item);
        target.dispatchEvent(new Event('pointerenter'));
        const peek = document.querySelector('.ta-annotation-peek') as HTMLButtonElement;
        expect(peek.hidden).toBe(false);
        expect(peek.textContent).toContain('想法');
        expect(peek.textContent).toContain('我的想法');
        expect((document.querySelector('.ta-inline-composer') as HTMLElement).hidden).toBe(true);
        (peek.querySelector('.ta-peek-edit') as HTMLButtonElement).click();

        expect(document.querySelector('.ta-panel')?.classList.contains('ta-open')).toBe(false);
        const composer = document.querySelector('.ta-inline-composer') as HTMLElement;
        expect(composer.hidden).toBe(false);
        expect(composer.textContent).toContain('编辑想法');
        expect((composer.querySelector('textarea') as HTMLTextAreaElement).value).toBe('我的想法');
    });

    it('opens a read-only thought without bubbling page-turn events and edits on demand', async () => {
        const item = { id: 15, kind: 'note', quote: '可点击原文', content: '直接编辑', locator: {}, color: '#f6c85f' };
        vi.spyOn(globalThis, 'fetch')
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [item] }) as never)
            .mockImplementationOnce(() => response({ err: 'ok' }) as never)
            .mockImplementationOnce(() => response({ err: 'ok', annotations: [{ ...item, content: '原位更新' }] }) as never);
        const annotations = new TalebookAnnotations({ bookId: 7, format: 'pdf' });
        await vi.waitFor(() => expect(document.querySelector('[data-id="15"]')).not.toBeNull());
        const page = document.createElement('div');
        const target = document.createElement('span');
        page.append(target);
        document.body.append(page);
        HTMLElement.prototype.scrollIntoView = vi.fn();
        const turnPage = vi.fn();
        page.addEventListener('click', turnPage);

        annotations.bindAnnotationTarget(target, item);
        target.click();

        expect(turnPage).not.toHaveBeenCalled();
        const peek = document.querySelector('.ta-annotation-peek') as HTMLElement;
        expect(peek.hidden).toBe(false);
        expect(peek.textContent).toContain('直接编辑');
        const composer = document.querySelector('.ta-inline-composer') as HTMLElement;
        expect(document.querySelector('.ta-panel')?.classList.contains('ta-open')).toBe(false);
        expect(composer.hidden).toBe(true);
        (peek.querySelector('.ta-peek-edit') as HTMLButtonElement).click();
        expect(composer.hidden).toBe(false);
        const textarea = composer.querySelector('textarea') as HTMLTextAreaElement;
        expect(textarea.value).toBe('直接编辑');
        textarea.value = '原位更新';
        textarea.dispatchEvent(new Event('input'));
        (composer.querySelector('.ta-inline-save') as HTMLButtonElement).click();
        await vi.waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(3));
        expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/api/book/7/annotations/15', expect.objectContaining({ method: 'PUT' }));
        expect(JSON.parse((globalThis.fetch as never as ReturnType<typeof vi.fn>).mock.calls[1][1].body)).toMatchObject({ content: '原位更新' });
        target.dispatchEvent(new Event('pointerenter'));
        expect(peek.textContent).toContain('原位更新');
        expect(peek.textContent).not.toContain('直接编辑');
    });
});

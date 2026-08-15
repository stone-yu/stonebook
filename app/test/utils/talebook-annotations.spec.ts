import { afterEach, describe, expect, it, vi } from 'vitest';
import { TalebookAnnotations } from '../../public/static/annotations/talebook-annotations.js';

const response = (body: object) => Promise.resolve({ json: () => Promise.resolve(body) });

afterEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    history.replaceState({}, '', '/read/7');
});

describe('TalebookAnnotations', () => {
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
});

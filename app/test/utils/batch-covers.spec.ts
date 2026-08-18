import { describe, expect, it, vi } from 'vitest';
import { selectedBooks, uploadOneCoverToBooks } from '@/utils/batch-covers';

describe('batch cover utilities', () => {
    it('resolves selected ids to the corresponding loaded books', () => {
        const items = [{ id: 1, title: '一' }, { id: 2, title: '二' }];
        expect(selectedBooks(items, [2])).toEqual([{ id: 2, title: '二' }]);
        expect(selectedBooks(items, [{ id: 1 }])).toEqual([{ id: 1, title: '一' }]);
    });

    it('applies the same cover to every selected book and reports partial failure', async () => {
        const backend = vi.fn()
            .mockResolvedValueOnce({ err: 'ok' })
            .mockResolvedValueOnce({ err: 'failed' });
        const progress = vi.fn();
        const cover = new File(['cover'], 'cover.jpg', { type: 'image/jpeg' });

        const result = await uploadOneCoverToBooks(cover, [7, 8], backend, progress);

        expect(result).toEqual({ total: 2, succeeded: 1, failed: 1 });
        expect(backend).toHaveBeenNthCalledWith(1, '/book/7/edit', expect.objectContaining({ method: 'POST' }));
        expect(backend).toHaveBeenNthCalledWith(2, '/book/8/edit', expect.objectContaining({ method: 'POST' }));
        // the same cover file is reused for every book
        expect(backend.mock.calls[0][1].body.get('cover')).toBe(cover);
        expect(backend.mock.calls[1][1].body.get('cover')).toBe(cover);
        expect(progress).toHaveBeenLastCalledWith(2, 2);
    });

    it('skips non-numeric ids and reports the filtered total', async () => {
        const backend = vi.fn().mockResolvedValue({ err: 'ok' });
        const cover = new File(['c'], 'c.jpg', { type: 'image/jpeg' });

        const result = await uploadOneCoverToBooks(cover, [7, NaN, '8'], backend);

        expect(result).toEqual({ total: 2, succeeded: 2, failed: 0 });
        expect(backend).toHaveBeenCalledTimes(2);
    });
});

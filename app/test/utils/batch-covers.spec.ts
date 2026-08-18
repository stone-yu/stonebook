import { describe, expect, it, vi } from 'vitest';
import { selectedBooks, uploadBookCovers } from '@/utils/batch-covers';

describe('batch cover utilities', () => {
    it('resolves selected ids to the corresponding loaded books', () => {
        const items = [{ id: 1, title: '一' }, { id: 2, title: '二' }];
        expect(selectedBooks(items, [2])).toEqual([{ id: 2, title: '二' }]);
        expect(selectedBooks(items, [{ id: 1 }])).toEqual([{ id: 1, title: '一' }]);
    });

    it('uploads a distinct cover for every selected book and reports partial failure', async () => {
        const backend = vi.fn()
            .mockResolvedValueOnce({ err: 'ok' })
            .mockResolvedValueOnce({ err: 'failed' });
        const progress = vi.fn();
        const first = new File(['first'], 'first.jpg', { type: 'image/jpeg' });
        const second = new File(['second'], 'second.png', { type: 'image/png' });

        const result = await uploadBookCovers({ 7: first, 8: second }, backend, progress);

        expect(result).toEqual({ total: 2, succeeded: 1, failed: 1 });
        expect(backend).toHaveBeenNthCalledWith(1, '/book/7/edit', expect.objectContaining({ method: 'POST' }));
        expect(backend.mock.calls[0][1].body.get('cover')).toBe(first);
        expect(backend.mock.calls[1][1].body.get('cover')).toBe(second);
        expect(progress).toHaveBeenLastCalledWith(2, 2);
    });
});

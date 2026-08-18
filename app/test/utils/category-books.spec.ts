import { describe, expect, it } from 'vitest';
import { categoryPathMap, sortCategoryBooks } from '@/utils/category-books';

const tree = [
    { id: 1, name: '技术', children: [{ id: 2, name: '数据库', children: [] }] },
    { id: 3, name: '文学', children: [] },
];

describe('category book sorting', () => {
    it('builds complete category paths', () => {
        expect(categoryPathMap(tree).get(2)).toBe('技术 / 数据库');
    });

    it('sorts by category path then title and puts uncategorized books last', () => {
        const books = [
            { id: 4, title: '无分类' },
            { id: 3, title: '乙' },
            { id: 2, title: '甲' },
            { id: 1, title: '阿Q正传' },
        ];
        const assignments = { 1: 3, 2: 2, 3: 2 };
        expect(sortCategoryBooks(books, assignments, tree).map(book => book.id)).toEqual([2, 3, 1, 4]);
        expect(books.map(book => book.id)).toEqual([4, 3, 2, 1]);
    });
});

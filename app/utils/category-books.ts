type CategoryNode = {
    id: number
    name: string
    children?: CategoryNode[]
}

type Book = {
    id: number
    title?: string
}

export function categoryPathMap(tree: CategoryNode[]) {
    const paths = new Map<number, string>();
    const walk = (nodes: CategoryNode[], parents: string[]) => {
        for (const node of nodes) {
            const path = [...parents, node.name];
            paths.set(node.id, path.join(' / '));
            walk(node.children || [], path);
        }
    };
    walk(tree, []);
    return paths;
}

export function sortCategoryBooks(books: Book[], assignments: Record<string, number>, tree: CategoryNode[]) {
    const paths = categoryPathMap(tree);
    const collator = new Intl.Collator('zh-CN', { numeric: true, sensitivity: 'base' });
    const categoryFor = (book: Book) => paths.get(assignments[String(book.id)]) || '';

    return [...books].sort((left, right) => {
        const leftCategory = categoryFor(left);
        const rightCategory = categoryFor(right);
        if (!leftCategory && rightCategory) return 1;
        if (leftCategory && !rightCategory) return -1;
        const categoryOrder = collator.compare(leftCategory, rightCategory);
        if (categoryOrder !== 0) return categoryOrder;
        const titleOrder = collator.compare(left.title || '', right.title || '');
        return titleOrder || left.id - right.id;
    });
}

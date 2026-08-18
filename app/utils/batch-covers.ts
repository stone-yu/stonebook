type Book = { id: number }
type Backend = (url: string, options: { method: string, body: FormData }) => Promise<{ err: string }>

export function selectedBooks<T extends Book>(items: T[], selectedIds: Array<number | T>) {
    const ids = new Set(selectedIds.map(item => typeof item === 'object' ? item.id : item));
    return items.filter(item => ids.has(item.id));
}

export async function uploadOneCoverToBooks(
    file: File,
    bookIds: Array<number>,
    backend: Backend,
    onProgress: (done: number, total: number) => void = () => {},
) {
    const ids = bookIds.map(id => Number(id)).filter(id => Number.isFinite(id));
    let succeeded = 0;
    let failed = 0;
    for (const bookId of ids) {
        const formData = new FormData();
        formData.append('cover', file);
        try {
            const response = await backend(`/book/${bookId}/edit`, { method: 'POST', body: formData });
            if (response.err === 'ok') succeeded += 1;
            else failed += 1;
        } catch {
            failed += 1;
        }
        onProgress(succeeded + failed, ids.length);
    }
    return { total: ids.length, succeeded, failed };
}

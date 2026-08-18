type Book = { id: number }
type Backend = (url: string, options: { method: string, body: FormData }) => Promise<{ err: string }>

export function selectedBooks<T extends Book>(items: T[], selectedIds: Array<number | T>) {
    const ids = new Set(selectedIds.map(item => typeof item === 'object' ? item.id : item));
    return items.filter(item => ids.has(item.id));
}

export async function uploadBookCovers(
    files: Record<number, File>,
    backend: Backend,
    onProgress: (done: number, total: number) => void = () => {},
) {
    const entries = Object.entries(files).filter(([, file]) => file instanceof File);
    let succeeded = 0;
    let failed = 0;
    for (const [bookId, file] of entries) {
        const formData = new FormData();
        formData.append('cover', file);
        try {
            const response = await backend(`/book/${bookId}/edit`, { method: 'POST', body: formData });
            if (response.err === 'ok') succeeded += 1;
            else failed += 1;
        } catch {
            failed += 1;
        }
        onProgress(succeeded + failed, entries.length);
    }
    return { total: entries.length, succeeded, failed };
}

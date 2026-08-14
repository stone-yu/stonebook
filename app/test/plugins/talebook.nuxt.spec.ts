import { describe, it, expect } from 'vitest';
import { parseNdjson, resolveStatusAlert } from '~/plugins/talebook';

// 构造一个最小 Response：body.getReader() 按给定的 chunk 序列依次吐出数据。
// 用于验证 parseNdjson 的逐行解析与跨 chunk 拼接逻辑。
function fakeResponse(chunks: string[]) {
    const encoder = new TextEncoder();
    let i = 0;
    return {
        body: {
            getReader() {
                return {
                    read() {
                        if (i < chunks.length) {
                            return Promise.resolve({ done: false, value: encoder.encode(chunks[i++]) });
                        }
                        return Promise.resolve({ done: true, value: undefined });
                    }
                };
            }
        }
    };
}

async function collect(gen: AsyncGenerator) {
    const out = [];
    for await (const x of gen) out.push(x);
    return out;
}

describe('parseNdjson', () => {
    it('逐行解析完整的 NDJSON 流', async () => {
        const res = fakeResponse(['{"total":2}\n{"id":1}\n{"id":2}\n']);
        expect(await collect(parseNdjson(res))).toEqual([{ total: 2 }, { id: 1 }, { id: 2 }]);
    });

    it('拼接跨 chunk 被截断的行', async () => {
        const res = fakeResponse(['{"to', 'tal":2}\n{"id":', '1}\n']);
        expect(await collect(parseNdjson(res))).toEqual([{ total: 2 }, { id: 1 }]);
    });

    it('跳过空行与非法 JSON', async () => {
        const res = fakeResponse(['{"id":1}\n\nnot-json\n{"id":2}\n']);
        expect(await collect(parseNdjson(res))).toEqual([{ id: 1 }, { id: 2 }]);
    });
});

describe('resolveStatusAlert', () => {
    it('拿不到 status.json 时，回退到通用的"启动中"提示', () => {
        const alert = resolveStatusAlert(null);
        expect(alert.type).toBe('info');
        expect(alert.msg).toContain('启动中');
    });

    it('phase 仍为 starting 时，保持通用提示', () => {
        const alert = resolveStatusAlert({ schema: 1, phase: 'starting', steps: [] });
        expect(alert.type).toBe('info');
        expect(alert.msg).toContain('启动中');
    });

    it('phase 为 failed 且命中已知 code 时，展示具体建议并附带诊断页链接', () => {
        const alert = resolveStatusAlert({
            schema: 1,
            phase: 'failed',
            steps: [
                { name: 'permission', status: 'failed', code: 'permission_denied' },
                { name: 'nginx_config', status: 'pending', code: null },
            ],
        });
        expect(alert.type).toBe('error');
        expect(alert.msg).toContain('PUID/PGID');
        expect(alert.msg).toContain('/status_page.html');
    });

    it('检测到旧存储布局时要求人工迁移', () => {
        const alert = resolveStatusAlert({
            schema: 1,
            phase: 'failed',
            steps: [{ name: 'storage_layout', status: 'failed', code: 'legacy_storage_layout' }],
        });
        expect(alert.type).toBe('error');
        expect(alert.msg).toContain('/data/books');
        expect(alert.msg).toContain('/library');
    });

    it('phase 为 failed 但 code 未知时，展示兜底文案', () => {
        const alert = resolveStatusAlert({
            schema: 1,
            phase: 'failed',
            steps: [{ name: 'syncdb', status: 'failed', code: 'unknown_future_code' }],
        });
        expect(alert.type).toBe('error');
        expect(alert.msg).toContain('服务器启动失败');
    });
});

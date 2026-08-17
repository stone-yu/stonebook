import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');

function source(path: string) {
    return readFileSync(resolve(root, path), 'utf8');
}

describe('navigation shell cleanup', () => {
    it('removes the duplicate tag guide and sidebar extra content from the default header', () => {
        const header = source('components/AppHeader.vue');

        expect(header).not.toContain("href: '/nav'");
        expect(header).not.toContain('sidebar_extra_html');
        expect(header).toContain("href: '/tag'");
        expect(header).toContain("href: '/discover'");
    });

    it('removes the duplicate tag guide from built-in theme headers', () => {
        const header = source('components/themes/BuiltinThemeHeader.vue');

        expect(header).not.toContain("href: '/nav'");
        expect(header).toContain("href: '/tag'");
        expect(header).toContain("href: '/discover'");
    });

    it('removes fixed project links from both footer implementations', () => {
        const footers = [
            source('components/AppFooter.vue'),
            source('components/themes/BuiltinThemeFooter.vue'),
        ].join('\n');

        expect(footers).not.toContain('hub.docker.com');
        expect(footers).not.toContain('talebook.org');
        expect(footers).not.toContain('github.com/talebook');
    });

    it('uses the fork issue tracker for avatar feedback', () => {
        expect(source('components/AppHeader.vue'))
            .toContain('href="https://github.com/stone-yu/talebook/issues"');
    });
});

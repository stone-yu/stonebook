import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const source = (path: string) => readFileSync(resolve(root, path), 'utf8');

describe('reading workbench phase one', () => {
    it('uses existing personal reading APIs without inventing duration metrics', () => {
        const home = source('pages/index.vue');

        expect(home).toContain("$backend('/reading/stats')");
        expect(home).toContain("$backend('/shelf')");
        expect(home).toContain('current_reading_books');
        expect(home).not.toContain('readingDuration');
    });

    it('provides a unified discovery entry for local and network resources', () => {
        const discover = source('pages/discover.vue');

        expect(discover).toContain("href: '/library'");
        expect(discover).toContain("href: '/network'");
        expect(discover).toContain("path: '/search'");
    });

    it('submits discovery search from a standalone button', () => {
        const discover = source('pages/discover.vue');
        const fieldEnd = discover.indexOf('/>');
        const submitButton = discover.indexOf('type="submit"');

        expect(discover).toContain('@submit.prevent="searchBooks"');
        expect(submitButton).toBeGreaterThan(fieldEnd);
        expect(discover).not.toContain('v-field__append-inner');
    });

    it('keeps low-frequency capabilities on the More page', () => {
        const more = source('pages/more.vue');

        for (const path of ['/audios', '/hot', '/recent', '/opds-readme', '/webdav-readme']) {
            expect(more).toContain(`href:'${path}'`);
        }
        for (const path of ['/categories', '/author', '/publisher', '/tag', '/format', '/series']) {
            expect(more).not.toContain(`href:'${path}'`);
        }
    });

    it('keeps all book browsing filters under Find Books', () => {
        const discover = source('pages/discover.vue');

        for (const path of ['/categories', '/author', '/publisher', '/tag', '/format', '/series', '/rating']) {
            expect(discover).toContain(`href: '${path}'`);
        }
    });

    it('provides a stable Find Books return link on discovery child routes', () => {
        const layout = source('layouts/default.vue');
        const backLink = source('components/DiscoverBackLink.vue');

        expect(layout).toContain('<DiscoverBackLink v-if="isDiscoverChild" />');
        expect(layout).toContain("'/search', '/library', '/network', '/categories', '/author', '/publisher', '/tag', '/format', '/series', '/rating'");
        expect(backLink).toContain('to="/discover"');
    });

    it('provides four mobile primary navigation tasks', () => {
        const bottomNavigation = source('components/ReaderBottomNavigation.vue');

        for (const path of ["href: '/'", "href: '/user/shelf'", "href: '/discover'", "href: '/more'"]) {
            expect(bottomNavigation).toContain(path);
        }
    });
});

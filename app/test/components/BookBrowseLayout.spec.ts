// @vitest-environment happy-dom
import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { describe, expect, it } from 'vitest';
import BookBrowseLayout from '@/components/BookBrowseLayout.vue';

const vuetify = createVuetify({ components, directives });
global.ResizeObserver = require('resize-observer-polyfill');

describe('BookBrowseLayout', () => {
    it('keeps facets on the left and renders book results on the right', () => {
        const wrapper = mount(BookBrowseLayout, {
            props: {
                title: '鲁迅',
                books: [{ id: 7, title: '呐喊', img: '/cover.jpg' }],
                emptyText: '暂无书籍',
            },
            slots: { sidebar: '<aside data-testid="facets">分类列表</aside>' },
            global: { plugins: [vuetify] },
        });

        const columns = wrapper.findAllComponents({ name: 'VCol' });
        expect(columns[0].props('md')).toBe('3');
        expect(columns[1].props('md')).toBe('9');
        expect(wrapper.get('[data-testid="facets"]').text()).toBe('分类列表');
        expect(wrapper.text()).toContain('鲁迅');
        expect(wrapper.text()).toContain('呐喊');
    });
});

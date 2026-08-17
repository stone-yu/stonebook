// @vitest-environment happy-dom
import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { describe, expect, it } from 'vitest';
import FacetListPanel from '@/components/FacetListPanel.vue';

const vuetify = createVuetify({ components, directives });
global.ResizeObserver = require('resize-observer-polyfill');

describe('FacetListPanel', () => {
    it('renders grouped facets with counts and emits the selected item', async () => {
        const wrapper = mount(FacetListPanel, {
            props: {
                title: '标签导览',
                selectedKey: '文学',
                icon: 'mdi-tag-multiple',
                items: [
                    { key: 'all', name: '全部书籍', count: 12, icon: 'mdi-bookshelf' },
                    { key: 'heading-0', name: '主题', type: 'heading' },
                    { key: '文学', name: '文学', count: 4 },
                ],
            },
            global: { plugins: [vuetify] },
        });

        expect(wrapper.text()).toContain('标签导览');
        expect(wrapper.text()).toContain('主题');
        expect(wrapper.text()).toContain('文学');
        expect(wrapper.find('.mdi-tag-multiple').exists()).toBe(true);

        const literary = wrapper.findAllComponents({ name: 'VListItem' })
            .find(item => item.text().includes('文学'));
        await literary?.trigger('click');
        expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ key: '文学', count: 4 });
    });
});

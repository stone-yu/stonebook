import { mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { describe, expect, it, vi } from 'vitest';

vi.mock('vue-i18n', () => ({
    useI18n: () => ({ t: (key: string) => key }),
}));

const vuetify = createVuetify({ components, directives });
global.ResizeObserver = require('resize-observer-polyfill');

import CategoryTreePanel from '@/components/CategoryTreePanel.vue';

const tree = [{
    id: 1,
    name: '文学',
    depth: 1,
    count: 2,
    children: [{
        id: 2,
        name: '中国文学',
        depth: 2,
        count: 1,
        children: [{ id: 3, name: '鲁迅', depth: 3, count: 1, children: [] }],
    }],
}];

describe('CategoryTreePanel.vue', () => {
    it('renders nested categories with aggregate counts and emits selection', async () => {
        const wrapper = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '书库分类', tree, selectedId: 1, showUncategorized: true, uncategorizedCount: 4 },
        });

        const items = wrapper.findAll('.category-tree-item');
        expect(items.map(item => item.text())).toEqual(expect.arrayContaining(['文学2', '中国文学1', '鲁迅1']));
        expect(wrapper.text()).toContain('category.uncategorized');
        expect(wrapper.text()).toContain('4');

        await wrapper.get('[data-category-id="3"]').trigger('click');
        expect(wrapper.emitted('select')).toContainEqual([3]);
    });

    it('shows management actions only when management is enabled', () => {
        const readonly = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '分类', tree, selectedId: 1 },
        });
        expect(readonly.text()).not.toContain('category.rename');

        const manageable = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '分类', tree, selectedId: 1, manageable: true },
        });
        expect(manageable.text()).toContain('category.rename');
        expect(manageable.text()).toContain('category.merge');
    });

    it('emits a separate shelf action without selecting the category', async () => {
        const wrapper = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '分类', tree, shelfable: true },
        });

        await wrapper.get('[data-category-id="1"] .category-shelf-action').trigger('click');
        expect(wrapper.emitted('add-to-shelf')).toEqual([[expect.objectContaining({ id: 1 })]]);
        expect(wrapper.emitted('select')).toBeUndefined();
    });

    it('emits a remove-from-shelf action when removable and the category has books', async () => {
        const wrapper = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '分类', tree, removable: true },
        });

        await wrapper.get('[data-category-id="1"] .category-remove-action').trigger('click');
        expect(wrapper.emitted('remove-from-shelf')).toEqual([[expect.objectContaining({ id: 1 })]]);
        expect(wrapper.emitted('select')).toBeUndefined();
    });

    it('does not render a remove action for an empty category', () => {
        const emptyTree = [{ id: 9, name: '空分类', depth: 1, count: 0, children: [] }];
        const wrapper = mount(CategoryTreePanel, {
            global: { plugins: [vuetify] },
            props: { title: '分类', tree: emptyTree, removable: true },
        });
        expect(wrapper.find('[data-category-id="9"] .category-remove-action').exists()).toBe(false);
    });
});

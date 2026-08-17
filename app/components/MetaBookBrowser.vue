<template>
    <BookBrowseLayout
        :title="selectedTitle"
        :books="books"
        :loading="loading"
        :error="error"
        :empty-text="t('category.empty')"
        :key-prefix="`facet-${metaType}`"
        :page="page"
        :pages="pages"
        @page="loadBooks"
    >
        <template #sidebar>
            <FacetListPanel
                :title="title"
                :items="facetItems"
                :selected-key="selectedKey"
                :icon="icon"
                @select="selectFacet"
            />
        </template>
    </BookBrowseLayout>
</template>

<script setup>
import BookBrowseLayout from '@/components/BookBrowseLayout.vue';
import FacetListPanel from '@/components/FacetListPanel.vue';
import { useMainStore } from '@/stores/main';
import { useI18n } from 'vue-i18n';

const props = defineProps({
    metaType: { type: String, required: true },
    titleKey: { type: String, required: true },
    icon: { type: String, required: true },
});
const { $backend } = useNuxtApp();
const route = useRoute();
const router = useRouter();
const store = useMainStore();
const { t } = useI18n();
const items = ref([]);
const books = ref([]);
const selectedName = ref(typeof route.query.name === 'string' ? route.query.name : '');
const loading = ref(false);
const error = ref('');
const page = ref(Math.max(1, Number(route.query.page) || 1));
const total = ref(0);
const pageSize = 60;
const title = computed(() => t(props.titleKey));
const selectedKey = computed(() => selectedName.value || 'all');
const selectedTitle = computed(() => selectedName.value || t('category.allBooks'));
const pages = computed(() => Math.ceil(total.value / pageSize));
const facetItems = computed(() => [
    { key: 'all', name: t('category.allBooks'), count: store.sys.books || undefined, icon: 'mdi-bookshelf' },
    ...items.value.map(item => ({ key: item.name, name: item.name, count: item.count })),
]);

async function loadFacets() {
    const rsp = await $backend(`/${props.metaType}?show=all`);
    if (rsp.err === 'ok' || rsp.items) items.value = rsp.items || [];
}
async function loadBooks(nextPage = page.value) {
    loading.value = true;
    error.value = '';
    page.value = Number(nextPage) || 1;
    const query = new URLSearchParams({ start: String((page.value - 1) * pageSize), size: String(pageSize) });
    if (selectedName.value) query.set(props.metaType, selectedName.value);
    try {
        const rsp = await $backend(`/library?${query}`);
        if (rsp.err === 'ok') {
            books.value = rsp.books || [];
            total.value = rsp.total || 0;
        } else error.value = rsp.msg || t('errors.networkError');
    } catch (exception) {
        error.value = t('errors.networkError');
    } finally {
        loading.value = false;
    }
}
function selectFacet(item) {
    selectedName.value = item.key === 'all' ? '' : item.name;
    page.value = 1;
    router.replace({ query: selectedName.value ? { name: selectedName.value } : {} });
    loadBooks(1);
}

watch(page, (value) => {
    const query = {};
    if (selectedName.value) query.name = selectedName.value;
    if (value > 1) query.page = String(value);
    router.replace({ query });
});

onMounted(async () => {
    store.setNavbar(true);
    await Promise.all([loadFacets(), loadBooks()]);
});
useHead(() => ({ title: title.value }));
</script>

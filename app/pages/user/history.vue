<template>
    <BookBrowseLayout
        :title="activeTitle"
        :books="activeBooks"
        :empty-text="activeEmptyText"
        key-prefix="reading-history"
    >
        <template #sidebar>
            <FacetListPanel
                :title="t('user.readingRecord.pageTitle')"
                :items="historyFacets"
                :selected-key="activeView"
                icon="mdi-book-clock"
                @select="selectView"
            />
        </template>
        <template
            v-if="activeView === 'history'"
            #default
        >
            <div
                v-if="history.length === 0"
                class="text-center py-8 text-grey"
            >
                {{ t('user.history.noHistory') }}
            </div>
            <template v-else>
                <section
                    v-for="item in history"
                    :key="item.name"
                    class="mb-6"
                >
                    <h2 class="text-subtitle-1 font-weight-bold mb-2">
                        {{ item.name }}
                    </h2>
                    <BookCoverGrid
                        :books="item.books"
                        :empty-text="t('user.history.noRecords')"
                        :key-prefix="`history-${item.name}`"
                        :show-title="true"
                        :md="2"
                    />
                </section>
            </template>
        </template>
    </BookBrowseLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import BookBrowseLayout from '@/components/BookBrowseLayout.vue';
import BookCoverGrid from '@/components/BookCoverGrid.vue';
import FacetListPanel from '@/components/FacetListPanel.vue';
import { useMainStore } from '@/stores/main';
import { useI18n } from 'vue-i18n';

const { $backend } = useNuxtApp();
const mainStore = useMainStore();
const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const activeView = ref(route.query.tab === 'finished' ? 'finished' : route.query.tab === 'history' ? 'history' : 'reading');
const user = ref({});
const readingBooks = ref([]);
const finishedBooks = ref([]);
const historyFacets = computed(() => [
    { key: 'reading', name: t('user.readingRecord.currentlyReading'), count: readingBooks.value.length, icon: 'mdi-book-open-page-variant' },
    { key: 'finished', name: t('user.readingRecord.finishedReading'), count: finishedBooks.value.length, icon: 'mdi-check-circle' },
    { key: 'history', name: t('user.readingRecord.readingRecord'), icon: 'mdi-history' },
]);
const activeBooks = computed(() => activeView.value === 'finished' ? finishedBooks.value : readingBooks.value);
const activeTitle = computed(() => historyFacets.value.find(item => item.key === activeView.value)?.name || '');
const activeEmptyText = computed(() => activeView.value === 'finished'
    ? t('user.readingRecord.noFinishedReading')
    : t('user.readingRecord.noCurrentlyReading'));
const getHistory = value => (value || []).map(book => ({ ...book, href: `/book/${book.id}` }));
const history = computed(() => {
    if (user.value.extra === undefined) return [];
    return [
        { name: t('user.history.onlineReading'), books: getHistory(user.value.extra.read_history) },
        { name: t('user.history.pushedBooks'), books: getHistory(user.value.extra.push_history) },
        { name: t('user.history.browseHistory'), books: getHistory(user.value.extra.visit_history) },
    ];
});

function selectView(item) {
    activeView.value = item.key;
    router.replace({ query: item.key === 'reading' ? {} : { tab: item.key } });
}
watch(() => route.query.tab, (tab) => {
    activeView.value = tab === 'finished' ? 'finished' : tab === 'history' ? 'history' : 'reading';
});
async function loadBooks(endpoint, target) {
    try {
        const rsp = await $backend(endpoint);
        if (rsp.err === 'ok') target.value = rsp.books || [];
    } catch (error) {
        console.error(`Failed to load ${endpoint}:`, error);
    }
}

onMounted(async () => {
    mainStore.setNavbar(true);
    await Promise.all([
        loadBooks('/reading', readingBooks),
        loadBooks('/read-done', finishedBooks),
        $backend('/user/info?detail=1').then(rsp => { user.value = rsp.user || {}; }),
    ]);
});
useHead({ title: () => t('user.readingRecord.pageTitle') });
</script>

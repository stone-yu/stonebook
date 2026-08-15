<template>
    <v-container fluid>
        <v-row>
            <v-col
                cols="12"
                md="3"
            >
                <CategoryTreePanel
                    :title="t('category.shelfTitle')"
                    :tree="tree"
                    :selected-id="selectedId"
                    manageable
                    :show-uncategorized="viewMode === 'annotations'"
                    @select="selectCategory"
                    @operate="operate"
                />
            </v-col>
            <v-col
                cols="12"
                md="9"
            >
                <div class="d-flex align-center mb-3">
                    <h1 class="text-h5">
                        {{ t('shelf.pageTitle') }}
                    </h1><v-spacer />
                    <v-switch
                        v-if="selectedId"
                        v-model="recursive"
                        :label="t('category.includeDescendants')"
                        hide-details
                        @update:model-value="loadCurrent"
                    />
                </div>
                <v-tabs
                    v-model="viewMode"
                    color="primary"
                    class="mb-4"
                    @update:model-value="loadCurrent"
                >
                    <v-tab
                        value="books"
                        prepend-icon="mdi-bookshelf"
                    >
                        {{ t('annotation.booksTab') }}
                    </v-tab>
                    <v-tab
                        value="annotations"
                        prepend-icon="mdi-format-quote-open"
                    >
                        {{ t('annotation.annotationsTab') }}
                    </v-tab>
                </v-tabs>
                <template v-if="viewMode === 'books'">
                    <div
                        v-if="books.length === 0"
                        class="text-center py-8 text-grey"
                    >
                        {{ t('shelf.empty') }}
                    </div>
                    <v-row v-else>
                        <v-col
                            v-for="book in books"
                            :key="book.id"
                            cols="4"
                            sm="3"
                            md="2"
                        >
                            <v-card>
                                <NuxtLink :to="`/book/${book.id}`">
                                    <v-img
                                        :src="book.img"
                                        :aspect-ratio="11 / 15"
                                    />
                                </NuxtLink>
                                <v-card-subtitle class="text-truncate px-2">
                                    {{ book.title }}
                                </v-card-subtitle>
                                <v-card-actions>
                                    <v-btn
                                        size="small"
                                        block
                                        prepend-icon="mdi-folder-edit"
                                        @click="editBook(book)"
                                    >
                                        {{ t('category.organize') }}
                                    </v-btn>
                                </v-card-actions>
                            </v-card>
                        </v-col>
                    </v-row>
                </template>
                <template v-else>
                    <div class="d-flex flex-wrap ga-2 mb-4">
                        <v-text-field
                            v-model="annotationQuery"
                            :label="t('annotation.search')"
                            prepend-inner-icon="mdi-magnify"
                            density="compact"
                            hide-details
                            clearable
                            style="max-width: 320px"
                            @keyup.enter="loadAnnotations"
                        />
                        <v-select
                            v-model="annotationKind"
                            :items="annotationKinds"
                            item-title="title"
                            item-value="value"
                            density="compact"
                            hide-details
                            style="max-width: 180px"
                            @update:model-value="loadAnnotations"
                        />
                        <v-btn-toggle
                            v-model="specialView"
                            mandatory
                            density="compact"
                            @update:model-value="loadAnnotations"
                        >
                            <v-btn value="normal">
                                {{ t('annotation.currentShelf') }}
                            </v-btn>
                            <v-btn value="detached">
                                {{ t('annotation.detached') }}
                            </v-btn>
                            <v-btn value="deleted">
                                {{ t('annotation.deleted') }}
                            </v-btn>
                        </v-btn-toggle>
                    </div>
                    <div
                        v-if="annotations.length === 0"
                        class="text-center py-10 text-grey"
                    >
                        {{ t('annotation.empty') }}
                    </div>
                    <v-card
                        v-for="item in annotations"
                        v-else
                        :key="item.id"
                        class="annotation-card mb-3"
                        variant="outlined"
                        :style="{ borderInlineStart: `4px solid ${item.color}` }"
                        @click="openAnnotation(item)"
                    >
                        <v-card-title class="text-subtitle-1 d-flex align-center">
                            <span class="text-truncate">{{ item.book_title }}</span><v-spacer />
                            <v-chip
                                size="small"
                                variant="tonal"
                            >
                                {{ item.chapter || t('annotation.location') }}
                            </v-chip>
                        </v-card-title>
                        <v-card-text>
                            <blockquote
                                v-if="item.quote"
                                class="annotation-quote"
                            >
                                {{ item.quote }}
                            </blockquote>
                            <p
                                v-if="item.content"
                                class="mt-2 mb-0 font-weight-medium"
                            >
                                {{ item.content }}
                            </p>
                            <div class="text-caption text-grey mt-2">
                                {{ item.book_authors }} · {{ formatDate(item.update_time) }}
                                <span v-if="item.book_deleted"> · {{ t('annotation.sourceDeleted') }}</span>
                            </div>
                        </v-card-text>
                    </v-card>
                </template>
                <v-alert
                    v-if="error"
                    type="error"
                    class="mt-4"
                >
                    {{ error }}
                </v-alert>
            </v-col>
        </v-row>

        <v-dialog
            v-model="bookDialog"
            max-width="520"
        >
            <v-card>
                <v-card-title>{{ t('category.organizeBook', { title: activeBook?.title || '' }) }}</v-card-title>
                <v-card-text>
                    <v-select
                        v-model="activeCategoryIds"
                        :items="categoryOptions"
                        item-title="title"
                        item-value="value"
                        multiple
                        chips
                        :label="t('category.personalCategories')"
                    />
                </v-card-text>
                <v-card-actions>
                    <v-spacer /><v-btn @click="bookDialog = false">
                        {{ t('common.cancel') }}
                    </v-btn><v-btn
                        color="primary"
                        @click="saveBookCategories"
                    >
                        {{ t('common.save') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import CategoryTreePanel from '@/components/CategoryTreePanel.vue';
import { useMainStore } from '@/stores/main';
import { useI18n } from 'vue-i18n';

const { $backend } = useNuxtApp();
const mainStore = useMainStore();
const { t } = useI18n();
const tree = ref([]);
const books = ref([]);
const annotations = ref([]);
const viewMode = ref('books');
const annotationQuery = ref('');
const annotationKind = ref('');
const specialView = ref('normal');
const selectedId = ref(null);
const recursive = ref(true);
const error = ref('');
const bookDialog = ref(false);
const activeBook = ref(null);
const activeCategoryIds = ref([]);
const annotationKinds = computed(() => [
    { title: t('annotation.allTypes'), value: '' },
    { title: t('annotation.highlight'), value: 'highlight' },
    { title: t('annotation.note'), value: 'note' },
]);

const flatten = nodes => nodes.flatMap(node => [node, ...flatten(node.children || [])]);
const categoryOptions = computed(() => flatten(tree.value).map(node => ({
    title: `${'— '.repeat(Math.max(0, node.depth - 1))}${node.name}`,
    value: node.id,
})));

async function loadTree() {
    const rsp = await $backend('/shelf/categories');
    if (rsp.err === 'ok') tree.value = rsp.tree || [];
}
async function loadBooks() {
    const url = selectedId.value
        ? `/shelf/categories/${selectedId.value}/books?recursive=${recursive.value}`
        : '/shelf';
    const rsp = await $backend(url);
    if (rsp.err === 'ok') books.value = rsp.books || [];
    else error.value = rsp.msg;
}
async function loadAnnotations() {
    const params = new URLSearchParams({ recursive: String(recursive.value), size: '100' });
    if (selectedId.value !== null && specialView.value === 'normal') params.set('category_id', selectedId.value);
    if (specialView.value === 'detached') params.set('detached', 'true');
    if (specialView.value === 'deleted') params.set('deleted', 'true');
    if (annotationKind.value) params.set('kind', annotationKind.value);
    if (annotationQuery.value) params.set('q', annotationQuery.value);
    const rsp = await $backend(`/shelf/annotations?${params}`);
    if (rsp.err === 'ok') annotations.value = rsp.annotations || [];
    else error.value = rsp.msg;
}
function loadCurrent() { return viewMode.value === 'books' ? loadBooks() : loadAnnotations(); }
function selectCategory(id) { selectedId.value = id; specialView.value = 'normal'; loadCurrent(); }
function openAnnotation(item) { if (item.target_url) window.open(item.target_url, '_blank', 'noopener'); }
function formatDate(value) { return value ? new Date(value).toLocaleDateString() : ''; }
async function operate(payload) {
    const rsp = await $backend('/shelf/categories', { method: 'POST', body: JSON.stringify(payload) });
    if (rsp.err !== 'ok') error.value = rsp.msg;
    else { error.value = ''; await loadTree(); await loadCurrent(); }
}
function editBook(book) {
    activeBook.value = book;
    activeCategoryIds.value = [...(book.shelf_category_ids || [])];
    bookDialog.value = true;
}
async function saveBookCategories() {
    const before = new Set(activeBook.value.shelf_category_ids || []);
    const after = new Set(activeCategoryIds.value);
    for (const categoryId of after) {
        if (!before.has(categoryId)) await operate({ action: 'assign', category_id: categoryId, book_id: activeBook.value.id });
    }
    for (const categoryId of before) {
        if (!after.has(categoryId)) await operate({ action: 'unassign', category_id: categoryId, book_id: activeBook.value.id });
    }
    bookDialog.value = false;
    await loadBooks();
}

useHead({ title: () => t('shelf.pageTitle') });
onMounted(async () => { mainStore.setNavbar(true); await loadTree(); await loadBooks(); });
</script>

<style scoped>
.annotation-card { cursor: pointer; transition: transform .15s ease, box-shadow .15s ease; }
.annotation-card:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgb(39 55 45 / 10%); }
.annotation-quote { margin: 0; padding-inline-start: 14px; border-inline-start: 2px solid rgb(73 106 86 / 35%); color: rgb(var(--v-theme-on-surface-variant)); white-space: pre-wrap; }
</style>

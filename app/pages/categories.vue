<template>
    <div>
        <BookBrowseLayout
            :title="selectedTitle"
            :books="books"
            :loading="loading"
            :error="error"
            :empty-text="t('category.empty')"
            key-prefix="category"
        >
            <template #sidebar>
                <CategoryTreePanel
                    :title="t('category.libraryTitle')"
                    :tree="tree"
                    :selected-id="selectedId"
                    :manageable="Boolean(store.user.is_admin)"
                    show-uncategorized
                    :uncategorized-count="uncategorizedCount"
                    @select="selectCategory"
                    @operate="operate"
                />
            </template>
            <template #controls>
                <v-switch
                    v-if="selectedId && selectedId > 0"
                    v-model="recursive"
                    :label="t('category.includeDescendants')"
                    hide-details
                    @update:model-value="loadBooks"
                />
            </template>
            <template #default>
                <div
                    v-if="books.length === 0"
                    class="text-center py-8 text-grey"
                >
                    {{ t('category.empty') }}
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
                            <v-card-actions v-if="store.user.is_admin">
                                <v-btn
                                    size="small"
                                    block
                                    prepend-icon="mdi-folder-move"
                                    @click="editBook(book)"
                                >
                                    {{ t('category.moveBook') }}
                                </v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-col>
                </v-row>
            </template>
        </BookBrowseLayout>
        <v-dialog
            v-model="bookDialog"
            max-width="500"
        >
            <v-card>
                <v-card-title>{{ t('category.moveBookTitle', { title: activeBook?.title || '' }) }}</v-card-title><v-card-text>
                    <v-select
                        v-model="bookCategoryId"
                        :items="categoryOptions"
                        item-title="title"
                        item-value="value"
                        :label="t('category.libraryTitle')"
                        clearable
                    />
                </v-card-text><v-card-actions>
                    <v-spacer /><v-btn @click="bookDialog = false">
                        {{ t('common.cancel') }}
                    </v-btn><v-btn
                        color="primary"
                        @click="saveBookCategory"
                    >
                        {{ t('common.save') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import CategoryTreePanel from '@/components/CategoryTreePanel.vue';
import BookBrowseLayout from '@/components/BookBrowseLayout.vue';
import { useMainStore } from '@/stores/main';
import { useI18n } from 'vue-i18n';

const { $backend } = useNuxtApp();
const store = useMainStore();
const { t } = useI18n();
const tree = ref([]);
const books = ref([]);
const selectedId = ref(null);
const recursive = ref(true);
const uncategorizedCount = ref(0);
const error = ref('');
const loading = ref(false);
const assignments = ref({});
const bookDialog = ref(false);
const activeBook = ref(null);
const bookCategoryId = ref(null);

const flatten = nodes => nodes.flatMap(node => [node, ...flatten(node.children || [])]);
const categoryOptions = computed(() => flatten(tree.value).map(node => ({
    title: `${'— '.repeat(Math.max(0, node.depth - 1))}${node.name}`,
    value: node.id,
})));
const selectedTitle = computed(() => {
    if (selectedId.value === null) return t('category.allBooks');
    if (selectedId.value === 0) return t('category.uncategorized');
    return flatten(tree.value).find(node => node.id === selectedId.value)?.name || t('category.libraryTitle');
});

async function loadTree() {
    const rsp = await $backend('/categories');
    if (rsp.err === 'ok') {
        tree.value = rsp.tree || [];
        uncategorizedCount.value = rsp.uncategorized_count || 0;
        assignments.value = rsp.book_categories || {};
    }
}
async function loadBooks() {
    error.value = '';
    loading.value = true;
    const url = selectedId.value === null ? '/library' : `/categories/${selectedId.value}/books?recursive=${recursive.value}`;
    try {
        const rsp = await $backend(url);
        if (rsp.err === 'ok') books.value = rsp.books || [];
        else error.value = rsp.msg;
    } catch (exception) {
        error.value = t('errors.networkError');
    } finally {
        loading.value = false;
    }
}
function selectCategory(id) { selectedId.value = id; loadBooks(); }
async function operate(payload) {
    const rsp = await $backend('/admin/categories', { method: 'POST', body: JSON.stringify(payload) });
    if (rsp.err !== 'ok') error.value = rsp.msg;
    else { error.value = ''; await loadTree(); await loadBooks(); }
}
function editBook(book) {
    activeBook.value = book;
    bookCategoryId.value = assignments.value[String(book.id)] || assignments.value[book.id] || null;
    bookDialog.value = true;
}
async function saveBookCategory() {
    const payload = bookCategoryId.value
        ? { action: 'assign', category_id: bookCategoryId.value, book_id: activeBook.value.id }
        : { action: 'unassign', book_id: activeBook.value.id };
    await operate(payload);
    bookDialog.value = false;
}

onMounted(async () => { store.setNavbar(true); await Promise.all([loadTree(), loadBooks()]); });
useHead({ title: () => t('category.libraryTitle') });
</script>

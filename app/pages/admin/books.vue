
<template>
    <v-card>
        <v-card-title class="pl-4">
            {{ t('admin.books.title') }} <v-chip
                size="small"
                variant="elevated"
                color="primary"
                class="ml-2"
            >
                Beta
            </v-chip>
        </v-card-title>
        <v-card-text class="pb-0"> {{ t('admin.books.message.bookTableInfo') }}</v-card-text>
        <v-card-actions class="pt-0">
            <v-btn
                :disabled="loading"
                variant="outlined"
                color="primary"
                @click="getDataFromApi"
            >
                <v-icon start>
                    mdi-reload
                </v-icon>{{ t('admin.books.button.refresh') }}
            </v-btn>
            <v-btn
                :disabled="loading"
                variant="outlined"
                color="info"
                @click="show_dialog_auto_file"
            >
                <v-icon start>
                    mdi-information
                </v-icon>{{ t('admin.books.button.autoUpdateBookInfo') }}
            </v-btn>
            <v-btn
                :disabled="loading"
                variant="outlined"
                color="info"
                @click="show_kindle_convert_dialog"
            >
                <v-icon start>
                    mdi-book-sync
                </v-icon>{{ t('admin.books.kindleConvert') }}
            </v-btn>
            <v-btn
                v-if="books_selected.length > 0"
                :disabled="loading"
                variant="outlined"
                color="primary"
                prepend-icon="mdi-image-multiple-outline"
                @click="openBatchCoverDialog"
            >
                {{ t('admin.books.button.batchCover') }} ({{ books_selected.length }})
            </v-btn>
            <v-btn
                v-if="books_selected.length > 0"
                :disabled="loading"
                variant="outlined"
                color="error"
                @click="delete_selected_books"
            >
                <v-icon start>
                    mdi-delete-alert
                </v-icon>{{ t('admin.books.button.bulkDelete') }} ({{ books_selected.length
                }})
            </v-btn>
            <v-spacer />
            <v-text-field
                v-model="search"
                density="compact"
                append-inner-icon="mdi-magnify"
                :label="t('admin.books.label.search')"
                single-line
                hide-details
            />
        </v-card-actions>
        
        <v-data-table-server
            v-model="books_selected"
            density="compact"
            class="elevation-1 text-body-2"
            show-select
            item-value="id"
            :search="search"
            :headers="headers"
            :items="items"
            :items-length="total"
            :loading="loading"
            :items-per-page="itemsPerPage"
            @update:options="updateOptions"
        >
            <template #item.status="{ item }">
                <v-chip
                    v-if="item.status == 'ready'"
                    size="small"
                    color="success"
                >
                    {{ t('admin.books.status.ready') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'exist'"
                    size="small"
                    color="grey-lighten-2"
                >
                    {{ t('admin.books.status.exist') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'imported'"
                    size="small"
                    color="primary"
                >
                    {{ t('admin.books.status.imported') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'new'"
                    size="small"
                    color="grey"
                >
                    {{ t('admin.books.status.new') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'downloading'"
                    size="small"
                    color="info"
                >
                    {{ t('admin.books.status.downloading') }}
                </v-chip>
                <v-tooltip
                    v-else-if="item.status == 'drop'"
                    :text="t('admin.imports.status.dropTooltip')"
                    location="top"
                >
                    <template #activator="{ props }">
                        <v-chip
                            size="small"
                            color="warning"
                            v-bind="props"
                        >
                            {{ t('admin.imports.status.drop') }}
                        </v-chip>
                    </template>
                </v-tooltip>
                <v-chip
                    v-else
                    size="small"
                    color="info"
                >
                    {{ item.status }}
                </v-chip>
            </template>
            
            <template #item.img="{ item }">
                <v-img
                    :src="item.img"
                    width="40"
                    height="60"
                    cover
                    class="cursor-pointer"
                    @click="editCover(item)"
                />
            </template>
            
            <template #item.id="{ item }">
                <a
                    class="press-content"
                    target="_blank"
                    :href="`/book/${item.id}`"
                >{{ item.id }}</a>
            </template>
            
            <template #item.title="{ item }">
                <div
                    class="cursor-pointer"
                    style="min-width: 120px; white-space: normal; word-break: break-word;"
                    @click="editField(item, 'title', t('admin.books.label.title'))"
                >
                    {{ item.title }}
                </div>
            </template>

            <template #item.authors="{ item }">
                <div
                    class="cursor-pointer"
                    style="min-width: 60px; white-space: normal; word-break: break-word;"
                    @click="editField(item, 'authors', t('admin.books.label.authors'))"
                >
                    <span v-if="item.authors">{{ item.authors.join("/") }}</span>
                    <span v-else> - </span>
                </div>
            </template>

            <template #item.rating="{ item }">
                <div
                    class="cursor-pointer"
                    @click="editField(item, 'rating', t('admin.books.label.rating'))"
                >
                    <span v-if="item.rating != null">{{ item.rating }} {{ t('admin.books.label.star') }}</span>
                    <span v-else> - </span>
                </div>
            </template>

            <template #item.publisher="{ item }">
                <div
                    class="cursor-pointer"
                    @click="editField(item, 'publisher', t('admin.books.label.publisher'))"
                >
                    {{ item.publisher || '-' }}
                </div>
            </template>

            <template #item.tags="{ item }">
                <div
                    class="cursor-pointer"
                    style="min-width: 200px; white-space: normal; word-break: break-word;"
                    @click="editField(item, 'tags', t('admin.books.label.tags'))"
                >
                    <span v-if="item.tags">{{ (tagsStr = item.tags.join("/"), tagsStr.slice(0, 77) + (tagsStr.length > 70 ? '...' : '')) }}</span>
                    <span v-else> - </span>
                </div>
            </template>

            <template #item.comments="{ item }">
                <div
                    class="cursor-pointer"
                    style="min-width: 300px; white-space: normal; word-break: break-word;"
                    @click="editField(item, 'comments', t('admin.books.label.comments'))"
                >
                    {{ item.comments ? item.comments.slice(0, 65) + (item.comments.length > 65 ? '...' : '') : '-' }}
                </div>
            </template>

            <template #item.actions="{ item }">
                <v-menu>
                    <template #activator="{ props }">
                        <v-btn
                            color="primary"
                            size="small"
                            v-bind="props"
                        >
                            {{ t('admin.books.user.action') }} <v-icon size="small">
                                mdi-dots-vertical
                            </v-icon>
                        </v-btn>
                    </template>
                    <v-list density="compact">
                        <v-list-item @click="delete_book(item)">
                            <v-list-item-title>{{ t('actions.deleteBook') }}</v-list-item-title>
                        </v-list-item>
                    </v-list>
                </v-menu>
            </template>
        </v-data-table-server>

        <!-- 通用编辑对话框 -->
        <v-dialog
            v-model="editDialog"
            width="500"
        >
            <v-card>
                <v-card-title>{{ t('common.edit') }}{{ editFieldLabel }}</v-card-title>
                <v-card-text>
                    <v-text-field
                        v-if="['title', 'publisher'].includes(editingField)"
                        v-model="editingValue"
                        :label="editFieldLabel"
                    />
                    <v-textarea
                        v-else-if="editingField === 'comments'"
                        v-model="editingValue"
                        :label="editFieldLabel"
                    />
                    <v-rating
                        v-else-if="editingField === 'rating'"
                        v-model="editingValue"
                        length="10"
                        dense
                    />
                    <v-combobox
                        v-else-if="['authors', 'tags'].includes(editingField)"
                        v-model="editingValue"
                        :items="editingValue"
                        multiple
                        chips
                    />
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        text
                        @click="editDialog = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        @click="saveField"
                    >
                        {{ t('common.save') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- 批量封面编辑对话框 -->
        <v-dialog
            v-model="batchCoverDialog"
            width="720"
            persistent
        >
            <v-card>
                <v-card-title>{{ t('admin.books.batchCoverTitle') }}</v-card-title>
                <v-card-subtitle>
                    {{ t('admin.books.batchCoverSubtitle', { count: batchCoverBooks.length }) }}
                </v-card-subtitle>
                <v-card-text class="batch-cover-list">
                    <div
                        v-for="book in batchCoverBooks"
                        :key="book.id"
                        class="batch-cover-row d-flex align-center ga-4 py-3"
                    >
                        <v-img
                            :src="book.img"
                            width="44"
                            height="62"
                            max-width="44"
                            cover
                            class="rounded"
                        />
                        <div class="batch-cover-book flex-grow-1">
                            <div class="text-body-2 font-weight-medium text-truncate">
                                {{ book.title }}
                            </div>
                            <div class="text-caption text-medium-emphasis">
                                ID {{ book.id }}
                            </div>
                        </div>
                        <v-file-input
                            :model-value="batchCoverFiles[book.id] || null"
                            class="batch-cover-input"
                            density="compact"
                            variant="outlined"
                            hide-details
                            accept="image/jpeg, image/png, image/gif"
                            prepend-icon=""
                            :label="t('book.selectCover')"
                            :disabled="batchCoverSaving"
                            @update:model-value="setBatchCoverFile(book.id, $event)"
                        />
                    </div>
                    <v-progress-linear
                        v-if="batchCoverSaving"
                        class="mt-4"
                        color="primary"
                        :model-value="batchCoverProgress.total ? batchCoverProgress.done / batchCoverProgress.total * 100 : 0"
                    />
                </v-card-text>
                <v-card-actions>
                    <span class="text-caption text-medium-emphasis px-2">
                        {{ t('admin.books.batchCoverSelected', {
                            selected: batchCoverFileCount,
                            total: batchCoverBooks.length,
                        }) }}
                    </span>
                    <v-spacer />
                    <v-btn
                        :disabled="batchCoverSaving"
                        @click="batchCoverDialog = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        :loading="batchCoverSaving"
                        :disabled="batchCoverFileCount === 0"
                        @click="saveBatchCovers"
                    >
                        {{ t('admin.books.button.uploadCovers') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- 封面编辑对话框 -->
        <v-dialog
            v-model="coverDialog"
            width="500"
        >
            <v-card>
                <v-card-title>{{ t('book.editCoverTitle') }}</v-card-title>
                <v-card-text>
                    <v-row>
                        <v-col
                            cols="12"
                            sm="6"
                        >
                            <v-img
                                :src="editingItem?.img"
                                max-height="200"
                                class="mb-4"
                                contain
                            />
                        </v-col>
                        <v-col
                            cols="12"
                            sm="6"
                        >
                            <v-file-input
                                v-model="coverFile"
                                accept="image/jpeg, image/png, image/gif"
                                :label="t('book.selectCover')"
                                prepend-icon="mdi-image"
                                @change="onCoverFileChange"
                            />
                            <small class="text-caption">{{ t('book.coverSupported') }}</small>
                        </v-col>
                    </v-row>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        text
                        @click="coverDialog = false"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-btn
                        color="primary"
                        @click="saveCover"
                    >
                        {{ t('common.save') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- 小浮窗提醒 -->
        <v-snackbar
            v-model="snack"
            top
            :timeout="3000"
            :color="snackColor"
        >
            {{ snackText }}
            <template #actions>
                <v-btn
                    variant="text"
                    @click="snack = false"
                >
                    {{ t('common.close') }}
                </v-btn>
            </template>
        </v-snackbar>

        <!-- 提醒拉取图书的规则说明 -->
        <v-dialog
            v-model="meta_dialog"
            persistent
            transition="dialog-bottom-transition"
            width="500"
        >
            <v-card>
                <v-toolbar
                    flat
                    density="compact"
                    dark
                    color="primary"
                    class="pl-4"
                >
                    {{ t('common.info') }}
                </v-toolbar>
                <v-card-text class="pt-4">
                    <p>{{ t('admin.books.message.aboutToFetch') }}</p>
                    <p>{{ t('admin.books.message.configInternetSource') }}</p>
                    <p>{{ t('admin.books.message.onlyUpdateBooksWithout') }}</p>
                    <p>{{ t('admin.books.message.limitedByServices') }}</p>
                    <br>
                    <template v-if="progress.total > 0">
                        <p>
                            {{ t('admin.books.message.currentProgress') }}<v-btn
                                size="small"
                                variant="text"
                                @click="refresh_progress"
                            >
                                {{ t('common.refresh') }}
                            </v-btn>
                        </p>
                        <p>
                            {{ t('admin.books.message.progressDetails', [progress.total, progress.done, progress.fail, progress.skip]) }}
                        </p>
                    </template>
                    <p v-else>
                        {{ t('admin.books.message.estimatedTime', [auto_fill_mins]) }}
                    </p>
                </v-card-text>
                <v-card-actions>
                    <v-btn @click="meta_dialog = !meta_dialog">
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-spacer />
                    <v-btn
                        color="primary"
                        @click="auto_fill"
                    >
                        {{ t('actions.start') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Kindle格式转EPUB确认对话框 -->
        <v-dialog
            v-model="kindle_convert_dialog"
            persistent
            width="500"
        >
            <v-card>
                <v-toolbar
                    flat
                    density="compact"
                    dark
                    color="info"
                    class="pl-4"
                >
                    {{ t('admin.books.reminderTitle') }}
                </v-toolbar>
                <v-card-text class="pt-4">
                    <p v-if="books_selected.length > 0">
                        {{ t('admin.books.kindleConvertSelectedConfirm', { count: books_selected.length }) }}
                    </p>
                    <p v-else>
                        {{ t('admin.books.kindleConvertAllConfirm') }}
                    </p>
                </v-card-text>
                <v-card-actions>
                    <v-btn @click="kindle_convert_dialog = false">
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-spacer />
                    <v-btn
                        color="info"
                        @click="kindleConvert"
                    >
                        {{ t('admin.books.execute') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- 批量删除确认对话框 -->
        <v-dialog
            v-model="delete_dialog"
            persistent
            width="500"
        >
            <v-card>
                <v-toolbar
                    flat
                    density="compact"
                    dark
                    color="error"
                    class="pl-4"
                >
                    {{ t('actions.confirmDelete') }}
                </v-toolbar>
                <v-card-text class="pt-4">
                    <p>{{ t('admin.books.message.confirmDeleteSelected', [books_selected.length]) }}</p>
                    <p class="text-medium-emphasis">
                        {{ t('admin.books.message.operationIrreversible') }}
                    </p>
                </v-card-text>
                <v-card-actions>
                    <v-btn @click="delete_dialog = !delete_dialog">
                        {{ t('common.cancel') }}
                    </v-btn>
                    <v-spacer />
                    <v-btn
                        color="error"
                        @click="confirm_delete_books"
                    >
                        {{ t('common.delete') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMainStore } from '@/stores/main';
import { selectedBooks, uploadBookCovers } from '@/utils/batch-covers';

const store = useMainStore();
const { $backend, $alert } = useNuxtApp();
const { t } = useI18n();

store.setNavbar(true);

const snack = ref(false);
const snackColor = ref('');
const snackText = ref('');
const meta_dialog = ref(false);
const delete_dialog = ref(false);
const kindle_convert_dialog = ref(false);
const coverFile = ref(null);
const batchCoverDialog = ref(false);
const batchCoverFiles = ref({});
const batchCoverSaving = ref(false);
const batchCoverProgress = ref({ done: 0, total: 0 });

const books_selected = ref([]);
const search = ref('');
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const itemsPerPage = ref(10);
const options = ref({ page: 1, itemsPerPage: 10, sortBy: [{ key: 'id', order: 'desc' }] });

const headers = computed(() => [
    { title: t('book.cover'), key: 'img', sortable: false, width: '80px' },
    { title: 'ID', key: 'id', sortable: true, width: '80px' },
    { title: t('book.field.title'), key: 'title', sortable: true, width: '200px' },
    { title: t('book.field.authors'), key: 'authors', sortable: true, width: '100px' },
    { title: t('book.field.rating'), key: 'rating', sortable: false, width: '60px' },
    { title: t('book.field.publisher'), key: 'publisher', sortable: false },
    { title: t('book.field.tags'), key: 'tags', sortable: true, width: '100px' },
    { title: t('book.field.comments'), key: 'comments', sortable: true },
    { title: t('admin.books.user.action'), key: 'actions', sortable: false },
]);

const progress = ref({
    skip: 0,
    fail: 0,
    done: 0,
    total: 0,
    status: 'finish',
});

const auto_fill_mins = computed(() => Math.floor(total.value / 60) + 1);
const batchCoverBooks = computed(() => selectedBooks(items.value, books_selected.value));
const batchCoverFileCount = computed(() => Object.values(batchCoverFiles.value).filter(Boolean).length);

// Edit dialog state
const editDialog = ref(false);
const editingItem = ref(null);
const editingField = ref('');
const editingValue = ref(null);
const editFieldLabel = ref('');

const coverDialog = ref(false);

const updateOptions = (newOptions) => {
    options.value = newOptions;
    // 同步更新 itemsPerPage，确保用户选择"全部"时能正确显示
    if (newOptions.itemsPerPage !== undefined) {
        itemsPerPage.value = newOptions.itemsPerPage;
    }
    getDataFromApi();
};

const getDataFromApi = () => {
    loading.value = true;
    const { page, itemsPerPage, sortBy } = options.value;
    
    // Vuetify 3 sortBy format: [{ key: 'id', order: 'desc' }]
    const sortKey = sortBy && sortBy.length ? sortBy[0].key : 'id';
    const sortOrder = sortBy && sortBy.length ? (sortBy[0].order === 'desc') : true;

    var data = new URLSearchParams();
    if (page != undefined) data.append('page', page);
    data.append('sort', sortKey);
    data.append('desc', sortOrder);
    if (itemsPerPage != undefined) data.append('num', itemsPerPage);
    if (search.value) data.append('search', search.value);

    $backend('/admin/book/list?' + data.toString())
        .then((rsp) => {
            if (rsp.err != 'ok') {
                items.value = [];
                total.value = 0;
                if ($alert) $alert('error', rsp.msg);
                return false;
            }
            items.value = rsp.items;
            total.value = rsp.total;
        })
        .finally(() => {
            loading.value = false;
        });
};

const refresh_progress = () => {
    $backend('/admin/book/fill', { method: 'GET' })
        .then((rsp) => {
            progress.value = rsp.status;
        });
};

const show_dialog_auto_file = () => {
    meta_dialog.value = true;
    refresh_progress();
};

const auto_fill = () => {
    $backend('/admin/book/fill', {
        method: 'POST',
        body: JSON.stringify({ 'idlist': 'all' }),
    })
        .then((rsp) => {
            meta_dialog.value = false;
            if (rsp.err != 'ok') {
                if ($alert) $alert('error', rsp.msg);
            }
            snack.value = true;
            snackColor.value = 'success';
            snackText.value = rsp.msg;
        });
};

const delete_book = (book) => {
    loading.value = true;
    $backend('/book/' + book.id + '/delete', {
        method: 'POST',
        body: '',
    })
        .then((rsp) => {
            if (rsp.err != 'ok') {
                if ($alert) $alert('error', rsp.msg);
            }
            snack.value = true;
            snackColor.value = 'success';
            snackText.value = rsp.msg;

            getDataFromApi();
        })
        .finally(() => {
            loading.value = false;
        });
};

const delete_selected_books = () => {
    if (books_selected.value.length === 0) {
        snack.value = true;
        snackColor.value = 'warning';
        snackText.value = t('admin.books.message.selectBooksFirst');
        return;
    }
    delete_dialog.value = true;
};

const confirm_delete_books = () => {
    if (books_selected.value.length === 0) {
        delete_dialog.value = false;
        return;
    }

    loading.value = true;
    delete_dialog.value = false;

    // v-data-table-server v-model returns IDs if item-value is set? 
    // Vuetify 3: if return-object is false (default), it returns values.
    // Wait, let's check. item-value="id". So books_selected should be array of IDs.
    const selectedIds = books_selected.value;

    $backend('/admin/book/delete', {
        method: 'POST',
        body: JSON.stringify({ idlist: selectedIds }),
    })
        .then((rsp) => {
            if (rsp.err != 'ok') {
                if ($alert) $alert('error', rsp.msg);
            } else {
                snack.value = true;
                snackColor.value = 'success';
                snackText.value = rsp.msg;
                books_selected.value = [];
                getDataFromApi();
            }
        })
        .finally(() => {
            loading.value = false;
        });
};

// Edit Field Logic
const editField = (item, field, label) => {
    editingItem.value = item;
    editingField.value = field;
    // Deep copy for arrays
    editingValue.value = Array.isArray(item[field]) ? [...item[field]] : item[field];
    editFieldLabel.value = label;
    editDialog.value = true;
};

const saveField = () => {
    const book = editingItem.value;
    const field = editingField.value;
    const value = editingValue.value;
    
    var edit = {};
    edit[field] = value;
    
    $backend('/book/' + book.id + '/edit', {
        method: 'POST',
        body: JSON.stringify(edit),
    }).then((rsp) => {
        if (rsp.err == 'ok') {
            snack.value = true;
            snackColor.value = 'success';
            snackText.value = rsp.msg;
            editDialog.value = false;
            getDataFromApi();
        } else {
            if ($alert) $alert('error', rsp.msg);
        }
    });
};

// Cover Edit Logic
const editCover = (item) => {
    editingItem.value = item;
    coverFile.value = null;
    coverDialog.value = true;
};

const onCoverFileChange = (e) => {
    // In Vuetify 3, v-file-input returns File[] or File.
    // v-model coverFile
    const file = Array.isArray(coverFile.value) ? coverFile.value[0] : coverFile.value;
    if (file) {
        if (file.size > 5 * 1024 * 1024) {
            if ($alert) $alert('error', t('admin.books.message.coverSizeLimit'));
            coverFile.value = null;
        }
    }
};

const saveCover = () => {
    const file = Array.isArray(coverFile.value) ? coverFile.value[0] : coverFile.value;
    
    if (!file) {
        if ($alert) $alert('info', t('admin.books.message.selectCoverFirst'));
        return;
    }

    loading.value = true;
    const formData = new FormData();
    formData.append('cover', file);

    $backend('/book/' + editingItem.value.id + '/edit', {
        method: 'POST',
        body: formData
    }).then((rsp) => {
        if (rsp.err == 'ok') {
            snack.value = true;
            snackColor.value = 'success';
            snackText.value = rsp.msg;
            coverDialog.value = false;
            getDataFromApi();
        } else {
            if ($alert) $alert('error', rsp.msg);
        }
    }).finally(() => {
        loading.value = false;
        coverFile.value = null;
    });
};

const openBatchCoverDialog = () => {
    batchCoverFiles.value = {};
    batchCoverProgress.value = { done: 0, total: 0 };
    batchCoverDialog.value = true;
};

const setBatchCoverFile = (bookId, value) => {
    const file = Array.isArray(value) ? value[0] : value;
    if (file && file.size > 5 * 1024 * 1024) {
        if ($alert) $alert('error', t('admin.books.message.coverSizeLimit'));
        delete batchCoverFiles.value[bookId];
        batchCoverFiles.value = { ...batchCoverFiles.value };
        return;
    }
    batchCoverFiles.value = { ...batchCoverFiles.value, [bookId]: file || null };
};

const saveBatchCovers = async () => {
    batchCoverSaving.value = true;
    batchCoverProgress.value = { done: 0, total: batchCoverFileCount.value };
    const result = await uploadBookCovers(batchCoverFiles.value, $backend, (done, totalFiles) => {
        batchCoverProgress.value = { done, total: totalFiles };
    });
    batchCoverSaving.value = false;
    if (result.failed === 0) {
        batchCoverDialog.value = false;
        books_selected.value = [];
        snack.value = true;
        snackColor.value = 'success';
        snackText.value = t('admin.books.message.batchCoverSuccess', { count: result.succeeded });
    } else if ($alert) {
        $alert('error', t('admin.books.message.batchCoverPartial', result));
    }
    getDataFromApi();
};

const show_kindle_convert_dialog = () => {
    kindle_convert_dialog.value = true;
};

const kindleConvert = () => {
    loading.value = true;
    kindle_convert_dialog.value = false;

    const body = {};
    if (books_selected.value.length > 0) {
        body.idlist = books_selected.value.map((book) => book.id);
    }

    $backend('/admin/book/kindleconvert', {
        method: 'POST',
        body: JSON.stringify(body),
    })
        .then((rsp) => {
            if (rsp.err === 'ok') {
                snack.value = true;
                snackColor.value = 'success';
                snackText.value = rsp.msg;
                books_selected.value = [];
                getDataFromApi();
            } else {
                if ($alert) $alert('error', rsp.msg);
            }
        })
        .finally(() => {
            loading.value = false;
        });
};

watch(search, () => {
    options.value.page = 1;
    getDataFromApi();
});

useHead(() => ({
    title: t('admin.books.title')
}));
</script>

<style scoped>
.cursor-pointer {
    cursor: pointer;
}

.batch-cover-list {
    max-height: min(62vh, 560px);
    overflow-y: auto;
}

.batch-cover-row + .batch-cover-row {
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.batch-cover-book {
    min-width: 0;
}

.batch-cover-input {
    flex: 0 1 300px;
}

/* 加宽分页选择器 */
:deep(.v-data-table-footer__items-per-page) {
    min-width: 120px;
}

:deep(.v-data-table-footer__items-per-page .v-field) {
    min-width: 100px;
}
</style>

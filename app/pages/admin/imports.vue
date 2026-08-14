<template>
    <v-card>
        <v-card-title class="pl-4">
            {{ t('admin.imports.title') }} <v-chip
                size="small"
                variant="elevated"
                color="primary ml-2"
            >
                Beta
            </v-chip>
        </v-card-title>
        <v-card-text>
            {{ t('admin.imports.message.importDirInfo', [scan_dir]) }}<br>
            {{ t('admin.imports.message.importAsyncInfo') }}<br>
            {{ t('admin.imports.message.calibreInfo') }}
        </v-card-text>
        <v-card-actions>
            <v-btn
                :disabled="loading"
                variant="outlined"
                color="primary"
                @click="getDataFromApi"
            >
                <v-icon start>
                    mdi-reload
                </v-icon>{{ t('admin.imports.button.refresh') }}
            </v-btn>
            <v-btn
                :disabled="loading"
                variant="elevated"
                color="primary"
                @click="scan_books"
            >
                <v-icon start>
                    mdi-file-find
                </v-icon>{{ t('admin.imports.button.scanBooks') }}
            </v-btn>
            <v-btn
                :disabled="loading"
                variant="elevated"
                color="primary"
                @click="openOpdsImportDialog"
            >
                <v-icon start>
                    mdi-database-import
                </v-icon>{{ t('admin.imports.button.importFromOpds') }}
            </v-btn>
            <template v-if="selected.length > 0">
                <v-btn
                    :disabled="loading"
                    variant="elevated"
                    color="#424242"
                    @click="import_books"
                >
                    <v-icon start>
                        mdi-import
                    </v-icon>{{ t('admin.imports.button.importSelectedBooks') }}
                </v-btn>
                <v-btn
                    :disabled="loading"
                    variant="outlined"
                    color="primary"
                    @click="delete_record"
                >
                    <v-icon start>
                        mdi-delete
                    </v-icon>{{ t('common.delete') }}
                </v-btn>
            </template>
            <template v-else>
                <v-btn
                    :disabled="loading"
                    variant="elevated"
                    color="warning"
                    @click="import_books"
                >
                    <v-icon start>
                        mdi-import
                    </v-icon>{{ t('admin.imports.button.importAllBooks') }}
                </v-btn>
            </template>
            <v-spacer />
            <v-checkbox
                v-model="auto_categorize"
                :label="t('admin.imports.label.autoCategorize')"
                color="primary"
                hide-details
            />
            <v-checkbox
                v-model="delete_after_import"
                :label="t('admin.imports.label.deleteAfterImport')"
                color="primary"
                hide-details
            />
        </v-card-actions>
        <v-card-text>
            <div v-if="selected.length == 0">
                {{ t('admin.imports.message.selectFilesInfo') }}
            </div>
            <div v-else>
                {{ t('admin.imports.message.selectedCount', [selected.length]) }}
            </div>
        </v-card-text>
        <v-tabs
            v-model="filter_type"
            @update:model-value="onFilterChange"
        >
            <v-tab value="todo">
                {{ t('admin.imports.tab.todo') }} ({{ count_todo }})
            </v-tab>
            <v-tab value="done">
                {{ t('admin.imports.tab.done') }} ({{ count_done }})
            </v-tab>
        </v-tabs>
        <v-data-table-server
            v-model="selected"
            density="compact"
            class="elevation-1 text-body-2"
            show-select
            item-value="hash"
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
                    {{ t('admin.imports.status.ready') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'exist'"
                    size="small"
                    color="grey-lighten-2"
                >
                    {{ t('admin.imports.status.exist') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'imported'"
                    size="small"
                    color="primary"
                >
                    {{ t('admin.imports.status.imported') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'new'"
                    size="small"
                    color="grey"
                >
                    {{ t('admin.imports.status.new') }}
                </v-chip>
                <v-chip
                    v-else-if="item.status == 'downloading'"
                    size="small"
                    color="info"
                >
                    {{ t('admin.imports.status.downloading') }}
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
            <template #item.title="{ item }">
                {{ t('admin.imports.label.bookTitle') }}：<span v-if="item.book_id == 0"> {{ item.title }} </span>
                <a
                    v-else
                    target="_blank"
                    :href="`/book/${item.book_id}`"
                >{{ item.title }}</a> <br>
                {{ t('admin.imports.label.author') }}：{{ item.author }}
            </template>
            <template #item.category_path="{ item }">
                <v-chip
                    v-if="item.category_path?.length"
                    size="small"
                    color="primary"
                    variant="tonal"
                >
                    {{ item.category_path.join(' / ') }}
                </v-chip>
                <span
                    v-else
                    class="text-medium-emphasis"
                >{{ t('category.uncategorized') }}</span>
                <div
                    v-if="item.category_error"
                    class="text-error text-caption"
                >
                    {{ item.category_error }}
                </div>
            </template>
        </v-data-table-server>
    </v-card>

    <OpdsImportDialog
        v-model:dialog-visible="opdsImportDialogVisible"
        @refresh-data="getDataFromApi"
    />
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMainStore } from '@/stores/main';
import OpdsImportDialog from '@/components/OpdsImportDialog.vue';

const store = useMainStore();
const { $backend, $alert } = useNuxtApp();
const { t } = useI18n();

store.setNavbar(true);

const filter_type = ref('todo');
const selected = ref([]);
const scan_dir = ref('/imports/');
const search = ref('');
const items = ref([]);
const total = ref(0);
const loading = ref(false);
const itemsPerPage = ref(100);
const options = ref({ page: 1, itemsPerPage: 100, sortBy: [{ key: 'create_time', order: 'desc' }] });

const count_todo = ref(0);
const count_done = ref(0);
const delete_after_import = ref(false);
const auto_categorize = ref(true);
const opdsImportDialogVisible = ref(false);

const scan_status = ref({});
const import_status = ref({});

const headers = computed(() => [
    { title: 'ID', key: 'id', sortable: true },
    { title: t('admin.imports.label.status'), key: 'status', sortable: true },
    { title: t('admin.imports.label.path'), key: 'path', sortable: true },
    { title: t('admin.imports.label.scanInfo'), key: 'title', sortable: false },
    { title: t('admin.imports.label.categoryPreview'), key: 'category_path', sortable: false },
    { title: t('admin.imports.label.time'), key: 'create_time', sortable: true, width: '200px' },
]);

const updateOptions = (newOptions) => {
    options.value = newOptions;
    if (newOptions.itemsPerPage !== undefined) {
        itemsPerPage.value = newOptions.itemsPerPage;
    }
    getDataFromApi();
};

const onFilterChange = () => {
    options.value.page = 1;
    getDataFromApi();
};

const getDataFromApi = () => {
    loading.value = true;
    const { page, itemsPerPage, sortBy } = options.value;

    const sortKey = sortBy && sortBy.length ? sortBy[0].key : 'create_time';
    const sortOrder = sortBy && sortBy.length ? (sortBy[0].order === 'desc') : true;

    const data = new URLSearchParams();
    data.append('filter', filter_type.value);
    if (page != undefined) data.append('page', page);
    data.append('sort', sortKey);
    data.append('desc', sortOrder);
    if (itemsPerPage != undefined) data.append('num', itemsPerPage);

    $backend('/admin/scan/list?' + data.toString())
        .then((rsp) => {
            if (rsp.err != 'ok') {
                items.value = [];
                total.value = 0;
                if ($alert) $alert('error', rsp.msg);
                return;
            }
            items.value = rsp.items;
            total.value = rsp.total;
            scan_dir.value = rsp.scan_dir;
            count_done.value = rsp.summary.done;
            count_todo.value = rsp.summary.todo;
        })
        .finally(() => {
            loading.value = false;
        });
};

const loop_check_status = (url, callback) => {
    setTimeout(() => {
        $backend(url)
            .then((rsp) => {
                if (rsp.err != 'ok') {
                    if ($alert) $alert('error', rsp.msg);
                    return;
                }
                if (callback(rsp)) {
                    getDataFromApi();
                    setTimeout(() => {
                        loop_check_status(url, callback);
                    }, 2000);
                } else {
                    getDataFromApi();
                    if ($alert) $alert('info', '处理完毕！');
                }
            });
    }, 2000);
};

const scan_books = () => {
    loading.value = true;
    $backend('/admin/scan/run', {
        method: 'POST',
    }).then((rsp) => {
        if (rsp.err !== 'ok') {
            if ($alert) $alert('error', rsp.msg);
            loading.value = false;
            return;
        }

        loop_check_status('/admin/scan/status', (rsp) => {
            scan_status.value = rsp.status;
            count_done.value = rsp.summary.done;
            count_todo.value = rsp.summary.todo;
            if (scan_status.value.new === 0) {
                loading.value = false;
                if (scan_status.value.new === 0 && scan_status.value.total > 0) {
                    $alert('success', '扫描完成！请查看"待处理"列表中的书籍。');
                }
                return false;
            }
            loading.value = true;
            return true;
        });
    }).catch((error) => {
        loading.value = false;
        if ($alert) $alert('error', error?.message || '扫描请求失败');
    });
};

const import_books = () => {
    loading.value = true;
    const hashlist = selected.value.length > 0 ? selected.value : 'all';

    $backend('/admin/import/run', {
        method: 'POST',
        body: JSON.stringify({
            hashlist: hashlist,
            delete_after: delete_after_import.value,
            auto_categorize: auto_categorize.value
        }),
    }).then((rsp) => {
        if (rsp.err !== 'ok') {
            if ($alert) $alert('error', rsp.msg);
        }

        loop_check_status('/admin/import/status', (rsp) => {
            import_status.value = rsp.status;
            count_done.value = rsp.summary.done;
            count_todo.value = rsp.summary.todo;
            if (import_status.value.ready === 0) {
                loading.value = false;
                return false;
            }
            loading.value = true;
            return true;
        });
    });
};

const delete_record = () => {
    loading.value = true;
    $backend('/admin/scan/delete', {
        method: 'POST',
        body: JSON.stringify({
            hashlist: selected.value
        }),
    }).then((rsp) => {
        if (rsp.err !== 'ok') {
            if ($alert) $alert('error', rsp.msg);
        }
        getDataFromApi();
        selected.value = [];
    }).finally(() => {
        loading.value = false;
    });
};

const openOpdsImportDialog = () => {
    opdsImportDialogVisible.value = true;
};

onMounted(() => {
    getDataFromApi();
});

useHead(() => ({
    title: t('admin.imports.title')
}));
</script>

<style scoped>
/* 加宽分页选择器 */
:deep(.v-data-table-footer__items-per-page) {
    min-width: 120px;
}

:deep(.v-data-table-footer__items-per-page .v-field) {
    min-width: 100px;
}
</style>

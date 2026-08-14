<template>
    <v-card variant="outlined">
        <v-card-title class="d-flex align-center">
            {{ title }}
            <v-spacer />
            <v-btn
                v-if="manageable"
                icon="mdi-plus"
                size="small"
                variant="text"
                :aria-label="t('category.addRoot')"
                @click="openDialog('create', null)"
            />
        </v-card-title>
        <v-list
            nav
            density="compact"
            :selected="selectedId === null ? ['all'] : [String(selectedId)]"
        >
            <v-list-item
                value="all"
                @click="$emit('select', null)"
            >
                <template #prepend>
                    <v-icon icon="mdi-bookshelf" />
                </template>
                <v-list-item-title>{{ t('category.allBooks') }}</v-list-item-title>
            </v-list-item>
            <v-list-item
                v-if="showUncategorized"
                value="0"
                @click="$emit('select', 0)"
            >
                <template #prepend>
                    <v-icon icon="mdi-folder-question" />
                </template>
                <v-list-item-title>{{ t('category.uncategorized') }}</v-list-item-title>
                <template #append>
                    <v-chip size="x-small">
                        {{ uncategorizedCount }}
                    </v-chip>
                </template>
            </v-list-item>
            <v-list-item
                v-for="item in flatNodes"
                :key="item.id"
                class="category-tree-item"
                :data-category-id="item.id"
                :value="String(item.id)"
                :style="{ paddingInlineStart: `${12 + (item.depth - 1) * 18}px` }"
                @click="$emit('select', item.id)"
            >
                <template #prepend>
                    <v-icon :icon="item.children.length ? 'mdi-folder' : 'mdi-folder-outline'" />
                </template>
                <v-list-item-title>{{ item.name }}</v-list-item-title>
                <template #append>
                    <v-chip size="x-small">
                        {{ item.count }}
                    </v-chip>
                </template>
            </v-list-item>
        </v-list>
        <v-divider v-if="manageable && selectedNode" />
        <v-card-actions
            v-if="manageable && selectedNode"
            class="flex-wrap"
        >
            <v-btn
                size="small"
                prepend-icon="mdi-folder-plus"
                @click="openDialog('create', selectedNode)"
            >
                {{ t('category.addChild') }}
            </v-btn>
            <v-btn
                size="small"
                prepend-icon="mdi-pencil"
                @click="openDialog('rename', selectedNode)"
            >
                {{ t('category.rename') }}
            </v-btn>
            <v-btn
                size="small"
                prepend-icon="mdi-folder-move"
                @click="openDialog('move', selectedNode)"
            >
                {{ t('category.move') }}
            </v-btn>
            <v-btn
                size="small"
                prepend-icon="mdi-call-merge"
                @click="openDialog('merge', selectedNode)"
            >
                {{ t('category.merge') }}
            </v-btn>
            <v-btn
                size="small"
                color="error"
                prepend-icon="mdi-delete"
                @click="$emit('operate', { action: 'delete', category_id: selectedNode.id })"
            >
                {{ t('common.delete') }}
            </v-btn>
        </v-card-actions>
    </v-card>

    <v-dialog
        v-model="dialog"
        max-width="480"
    >
        <v-card>
            <v-card-title>{{ dialogTitle }}</v-card-title>
            <v-card-text>
                <v-text-field
                    v-if="mode === 'create' || mode === 'rename'"
                    v-model="name"
                    :label="t('category.name')"
                    maxlength="100"
                    autofocus
                />
                <v-select
                    v-else
                    v-model="targetId"
                    :items="targetOptions"
                    item-title="title"
                    item-value="value"
                    :label="mode === 'move' ? t('category.targetParent') : t('category.mergeTarget')"
                    clearable
                />
            </v-card-text>
            <v-card-actions>
                <v-spacer /><v-btn @click="dialog = false">
                    {{ t('common.cancel') }}
                </v-btn><v-btn
                    color="primary"
                    @click="submit"
                >
                    {{ t('common.confirm') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
    title: { type: String, required: true },
    tree: { type: Array, default: () => [] },
    selectedId: { type: Number, default: null },
    manageable: { type: Boolean, default: false },
    showUncategorized: { type: Boolean, default: false },
    uncategorizedCount: { type: Number, default: 0 },
});
const emit = defineEmits(['select', 'operate']);
const { t } = useI18n();
const dialog = ref(false);
const mode = ref('create');
const activeNode = ref(null);
const name = ref('');
const targetId = ref(null);

const flatten = (nodes, result = []) => {
    for (const node of nodes) {
        result.push(node);
        flatten(node.children || [], result);
    }
    return result;
};
const flatNodes = computed(() => flatten(props.tree, []));
const selectedNode = computed(() => flatNodes.value.find(node => node.id === props.selectedId));
const targetOptions = computed(() => [
    { title: t('category.root'), value: null },
    ...flatNodes.value
        .filter(node => !activeNode.value || node.id !== activeNode.value.id)
        .map(node => ({ title: `${'— '.repeat(Math.max(0, node.depth - 1))}${node.name}`, value: node.id })),
]);
const dialogTitle = computed(() => t(`category.${mode.value}Title`));

function openDialog(nextMode, node) {
    mode.value = nextMode;
    activeNode.value = node;
    name.value = nextMode === 'rename' ? node?.name || '' : '';
    targetId.value = null;
    dialog.value = true;
}

function submit() {
    let payload;
    if (mode.value === 'create') payload = { action: 'create', name: name.value, parent_id: activeNode.value?.id || null };
    else if (mode.value === 'rename') payload = { action: 'update', category_id: activeNode.value.id, name: name.value };
    else if (mode.value === 'move') payload = { action: 'update', category_id: activeNode.value.id, parent_id: targetId.value };
    else payload = { action: 'merge', source_id: activeNode.value.id, target_id: targetId.value };
    emit('operate', payload);
    dialog.value = false;
}
</script>

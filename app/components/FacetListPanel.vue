<template>
    <v-card
        variant="outlined"
        class="facet-list-panel"
    >
        <v-card-title>{{ title }}</v-card-title>
        <v-list
            nav
            density="compact"
            :selected="[selectedKey]"
            class="facet-list"
        >
            <template
                v-for="item in items"
                :key="item.key"
            >
                <v-list-subheader v-if="item.type === 'heading'">
                    {{ item.name }}
                </v-list-subheader>
                <v-list-item
                    v-else
                    :value="item.key"
                    @click="$emit('select', item)"
                >
                    <template #prepend>
                        <v-icon :icon="item.icon || icon" />
                    </template>
                    <v-list-item-title>{{ item.name }}</v-list-item-title>
                    <template
                        v-if="item.count !== undefined"
                        #append
                    >
                        <v-chip size="x-small">
                            {{ item.count }}
                        </v-chip>
                    </template>
                </v-list-item>
            </template>
        </v-list>
    </v-card>
</template>

<script setup>
defineProps({
    title: { type: String, required: true },
    items: { type: Array, default: () => [] },
    selectedKey: { type: String, default: 'all' },
    icon: { type: String, default: 'mdi-label-outline' },
});
defineEmits(['select']);
</script>

<style scoped>
.facet-list-panel { position: sticky; top: 60px; }
.facet-list { max-height: calc(100vh - 130px); overflow-y: auto; }
@media (max-width: 959px) {
  .facet-list-panel { position: static; }
  .facet-list { max-height: 320px; }
}
</style>

<template>
    <v-container
        fluid
        class="book-browse-layout"
    >
        <v-row>
            <v-col
                cols="12"
                md="3"
            >
                <slot name="sidebar" />
            </v-col>
            <v-col
                cols="12"
                md="9"
            >
                <div class="d-flex align-center mb-3 book-browse-heading">
                    <h1 class="text-h5">
                        {{ title }}
                    </h1>
                    <v-spacer />
                    <slot name="controls" />
                </div>
                <v-progress-linear
                    v-if="loading"
                    indeterminate
                    color="primary"
                    class="mb-3"
                />
                <slot>
                    <BookCoverGrid
                        :books="books"
                        :empty-text="emptyText"
                        :key-prefix="keyPrefix"
                        :show-title="true"
                        :md="2"
                    />
                </slot>
                <v-alert
                    v-if="error"
                    type="error"
                    class="mt-4"
                >
                    {{ error }}
                </v-alert>
                <v-pagination
                    v-if="pages > 1"
                    :model-value="page"
                    :length="pages"
                    rounded="circle"
                    class="mt-5"
                    @update:model-value="$emit('page', $event)"
                />
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup>
import BookCoverGrid from '@/components/BookCoverGrid.vue';

defineProps({
    title: { type: String, default: '' },
    books: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    error: { type: String, default: '' },
    emptyText: { type: String, required: true },
    keyPrefix: { type: String, default: 'browse' },
    page: { type: Number, default: 1 },
    pages: { type: Number, default: 0 },
});
defineEmits(['page']);
</script>

<style scoped>
.book-browse-layout { padding-inline: 0; }
.book-browse-heading { min-height: 48px; }
@media (max-width: 959px) {
  .book-browse-heading { min-height: auto; }
}
</style>

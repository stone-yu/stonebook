<template>
    <v-bottom-navigation
        v-if="display.smAndDown.value"
        class="reader-bottom-nav"
        grow
        :model-value="activePath"
        color="primary"
        elevation="10"
    >
        <v-btn
            v-for="item in items"
            :key="item.href"
            :to="item.href"
            :value="item.href"
        >
            <v-icon>{{ item.icon }}</v-icon>
            <span>{{ item.text }}</span>
        </v-btn>
    </v-bottom-navigation>
</template>

<script setup>
import { computed } from 'vue';
import { useDisplay } from 'vuetify';
import { useI18n } from 'vue-i18n';

const display = useDisplay();
const route = useRoute();
const { t } = useI18n();

const items = computed(() => [
    { href: '/', icon: 'mdi-home', text: t('navigation.home') },
    { href: '/user/shelf', icon: 'mdi-bookshelf', text: t('navigation.myShelf') },
    { href: '/discover', icon: 'mdi-book-search-outline', text: t('navigation.findBooks') },
    { href: '/more', icon: 'mdi-menu', text: t('navigation.more') },
]);

const activePath = computed(() => {
    const match = items.value.find(item => item.href !== '/' && route.path.startsWith(item.href));
    return match?.href || '/';
});
</script>

<style scoped>
.reader-bottom-nav {
    backdrop-filter: blur(18px);
    background: rgba(var(--v-theme-surface), .92) !important;
    border-top: 1px solid rgba(var(--v-border-color), .12);
    z-index: 1100;
}

.reader-bottom-nav :deep(.v-btn) {
    min-width: 64px;
}
</style>

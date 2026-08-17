<template>
    <NuxtLink
        class="discover-back-link"
        to="/discover"
    >
        <v-icon size="18">
            mdi-arrow-left
        </v-icon>
        <span>{{ t('discover.back') }}</span>
    </NuxtLink>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
</script>

<style scoped>
.discover-back-link{align-items:center;color:rgba(var(--v-theme-on-surface),.68);display:inline-flex;font-size:.9rem;font-weight:600;gap:7px;margin:4px 0 18px;padding:8px 11px;text-decoration:none;transition:color .18s ease,transform .18s ease}.discover-back-link:hover{color:rgb(var(--v-theme-primary));transform:translateX(-2px)}.discover-back-link:focus-visible{border-radius:10px;outline:2px solid rgb(var(--v-theme-primary));outline-offset:2px}
</style>

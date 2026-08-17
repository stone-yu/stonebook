<template>
    <div class="more-page">
        <header><p>{{ t('more.eyebrow') }}</p><h1>{{ t('navigation.more') }}</h1><span>{{ t('more.subtitle') }}</span></header>
        <section
            v-for="section in sections"
            :key="section.title"
        >
            <h2>{{ section.title }}</h2>
            <div class="more-grid">
                <NuxtLink
                    v-for="item in section.items"
                    :key="item.href"
                    :to="item.href"
                >
                    <v-avatar color="surface-variant">
                        <v-icon>{{ item.icon }}</v-icon>
                    </v-avatar>
                    <div><strong>{{ item.title }}</strong><small>{{ item.description }}</small></div>
                    <v-icon size="18">
                        mdi-chevron-right
                    </v-icon>
                </NuxtLink>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMainStore } from '@/stores/main';
const store=useMainStore();const{t}=useI18n();store.setNavbar(true);useHead({title:()=>t('navigation.more')});
const sections=computed(()=>[
    {title:t('more.connections'),items:[
        {href:'/opds-readme',icon:'mdi-cellphone-link',title:t('messages.opdsIntroduction'),description:'OPDS'},
        {href:'/webdav-readme',icon:'mdi-cloud-sync-outline',title:t('messages.webdavIntroduction'),description:'WebDAV'},
    ]},
]);
</script>

<style scoped>
.more-page{display:grid;gap:30px;padding:12px 0 40px}.more-page header{background:linear-gradient(125deg,rgba(230,220,255,.55),rgba(255,234,220,.48));border-radius:26px;padding:32px}.more-page header p{color:rgb(var(--v-theme-primary));font-size:.76rem;font-weight:700;letter-spacing:.12em;margin:0;text-transform:uppercase}.more-page header h1{font-size:2.35rem;margin:4px 0}.more-page header span{color:rgba(var(--v-theme-on-surface),.58)}.more-page section h2{font-size:1rem;margin:0 0 12px}.more-grid{display:grid;gap:12px;grid-template-columns:1fr 1fr}.more-grid a{align-items:center;background:rgb(var(--v-theme-surface));border:1px solid rgba(var(--v-border-color),.1);border-radius:18px;color:inherit;display:grid;gap:14px;grid-template-columns:auto 1fr auto;padding:16px;text-decoration:none}.more-grid div{display:grid}.more-grid small{color:rgba(var(--v-theme-on-surface),.5);margin-top:3px}@media(max-width:700px){.more-page{padding-top:0}.more-page header{border-radius:22px;padding:24px}.more-grid{grid-template-columns:1fr}}
</style>

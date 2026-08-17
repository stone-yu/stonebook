<template>
    <div class="discover-page">
        <section class="discover-hero">
            <p>{{ t('discover.eyebrow') }}</p>
            <h1>{{ t('discover.title') }}</h1>
            <span>{{ t('discover.subtitle') }}</span>
            <v-form
                class="discover-search"
                @submit.prevent="searchBooks"
            >
                <v-text-field
                    v-model="keyword"
                    :placeholder="t('discover.placeholder')"
                    prepend-inner-icon="mdi-magnify"
                    hide-details
                    clearable
                    variant="solo"
                    rounded="xl"
                />
                <v-btn
                    class="discover-search-button"
                    color="primary"
                    rounded="xl"
                    size="large"
                    type="submit"
                >
                    {{ t('common.search') }}
                </v-btn>
            </v-form>
        </section>

        <section class="source-grid">
            <NuxtLink
                v-for="source in sources"
                :key="source.href"
                :to="source.href"
                :class="['source-card', source.tone]"
            >
                <v-icon size="32">
                    {{ source.icon }}
                </v-icon>
                <div><h2>{{ source.title }}</h2><p>{{ source.description }}</p></div>
                <v-icon>mdi-arrow-right</v-icon>
            </NuxtLink>
        </section>

        <section class="discover-section">
            <div class="section-heading">
                <p>{{ t('discover.refineEyebrow') }}</p>
                <h2>{{ t('discover.refineTitle') }}</h2>
            </div>
            <div class="filter-grid">
                <NuxtLink
                    v-for="item in filters"
                    :key="item.href"
                    :to="item.href"
                >
                    <v-icon>{{ item.icon }}</v-icon><span>{{ item.title }}</span><small>{{ item.count }}</small>
                </NuxtLink>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMainStore } from '@/stores/main';

const store = useMainStore();
const router = useRouter();
const { t } = useI18n();
const keyword = ref('');

store.setNavbar(true);
useHead({ title: () => t('discover.title') });

const sources = computed(() => [
    { href: '/library', icon: 'mdi-bookshelf', title: t('navigation.localLibrary'), description: t('discover.localDescription'), tone: 'source-blue' },
    ...(store.sys.show_network_library !== false
        ? [{ href: '/network', icon: 'mdi-cloud-search-outline', title: t('navigation.networkLibrary'), description: t('discover.networkDescription'), tone: 'source-mint' }]
        : []),
]);
const filters = computed(() => [
    { href: '/categories', icon: 'mdi-shape-outline', title: t('navigation.libraryCategories'), count: t('counts.books', { count: store.sys.books || 0 }) },
    { href: '/author', icon: 'mdi-account-voice', title: t('navigation.authors'), count: t('counts.authors', { count: store.sys.authors || 0 }) },
    { href: '/publisher', icon: 'mdi-domain', title: t('navigation.publishers'), count: t('counts.publishers', { count: store.sys.publishers || 0 }) },
    { href: '/tag', icon: 'mdi-tag-outline', title: t('navigation.tags'), count: t('counts.tags', { count: store.sys.tags || 0 }) },
    { href: '/format', icon: 'mdi-file-outline', title: t('navigation.formats'), count: t('counts.formats', { count: store.sys.formats || 0 }) },
    { href: '/series', icon: 'mdi-library-shelves', title: t('navigation.series'), count: t('counts.series', { count: store.sys.series || 0 }) },
    { href: '/rating', icon: 'mdi-star-outline', title: t('navigation.ratings'), count: t('discover.ratingDescription') },
    { href: '/hot', icon: 'mdi-trending-up', title: t('navigation.hot'), count: t('more.hotDesc') },
    { href: '/recent', icon: 'mdi-history', title: t('navigation.recent'), count: t('more.recentDesc') },
]);

function searchBooks() {
    const name = keyword.value.trim();
    if (name) router.push({ path: '/search', query: { name } });
}
</script>

<style scoped>
.discover-page{display:grid;gap:32px;padding:12px 0 40px}.discover-hero{background:linear-gradient(125deg,rgba(111,139,235,.18),rgba(183,170,237,.13),rgba(166,225,207,.16));border:1px solid rgba(var(--v-border-color),.08);border-radius:28px;padding:42px}.discover-hero>p,.section-heading p{color:rgb(var(--v-theme-primary));font-size:.76rem;font-weight:700;letter-spacing:.12em;margin:0 0 6px;text-transform:uppercase}.discover-hero h1{font-size:clamp(2rem,5vw,3.4rem);letter-spacing:-.05em;margin:0}.discover-hero>span{color:rgba(var(--v-theme-on-surface),.62);display:block;margin-top:10px}.discover-search{align-items:center;display:grid;gap:12px;grid-template-columns:minmax(0,1fr) auto;margin-top:30px;max-width:760px}.discover-search :deep(.v-field){box-shadow:0 14px 40px rgba(42,55,83,.1)}.discover-search-button{min-height:56px;padding-inline:28px}.source-grid{display:grid;gap:18px;grid-template-columns:1fr 1fr}.source-card{align-items:center;border:1px solid rgba(var(--v-border-color),.08);border-radius:22px;color:inherit;display:grid;gap:18px;grid-template-columns:auto 1fr auto;padding:24px;text-decoration:none}.source-card h2{font-size:1.16rem;margin:0 0 5px}.source-card p{color:rgba(var(--v-theme-on-surface),.58);margin:0}.source-blue{background:linear-gradient(135deg,rgba(214,226,255,.7),rgba(var(--v-theme-surface),.9))}.source-mint{background:linear-gradient(135deg,rgba(207,241,230,.72),rgba(var(--v-theme-surface),.9))}.discover-section{display:grid;gap:18px}.section-heading h2{margin:0}.filter-grid{display:grid;gap:14px;grid-template-columns:repeat(3,1fr)}.filter-grid a{background:rgb(var(--v-theme-surface));border:1px solid rgba(var(--v-border-color),.1);border-radius:18px;color:inherit;display:grid;gap:9px;padding:20px;text-decoration:none}.filter-grid small{color:rgba(var(--v-theme-on-surface),.5)}@media(max-width:900px){.filter-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.discover-page{padding-top:0}.discover-hero{border-radius:22px;padding:25px}.source-grid,.filter-grid{grid-template-columns:1fr}.discover-search{grid-template-columns:1fr}.discover-search-button{width:100%}}
</style>

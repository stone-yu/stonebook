<template>
    <div class="reading-home">
        <section class="home-hero">
            <div>
                <p class="home-eyebrow">
                    {{ t('workbench.eyebrow') }}
                </p>
                <h1>{{ greeting }}</h1>
                <p>{{ heroSummary }}</p>
            </div>
            <v-btn
                to="/discover"
                color="primary"
                size="large"
                prepend-icon="mdi-book-search-outline"
                rounded="xl"
            >
                {{ t('navigation.findBooks') }}
            </v-btn>
        </section>

        <section
            v-if="store.user.is_login"
            class="workbench-grid"
        >
            <v-card
                class="continue-card workbench-card"
                flat
            >
                <div class="section-heading">
                    <div>
                        <span>{{ t('workbench.continueReading') }}</span>
                        <h2>{{ currentBook?.title || t('workbench.noCurrentBook') }}</h2>
                    </div>
                    <v-chip
                        v-if="currentBook"
                        color="primary"
                        variant="tonal"
                    >
                        {{ t('workbench.inProgress') }}
                    </v-chip>
                </div>
                <div
                    v-if="currentBook"
                    class="continue-content"
                >
                    <v-img
                        :src="currentBook.img"
                        :alt="currentBook.title"
                        class="continue-cover"
                        cover
                    />
                    <div class="continue-copy">
                        <p>{{ bookAuthors(currentBook) }}</p>
                        <span>{{ lastReadLabel }}</span>
                        <v-btn
                            :to="`/book/${currentBook.id}`"
                            color="primary"
                            rounded="xl"
                            append-icon="mdi-arrow-right"
                        >
                            {{ t('workbench.continueAction') }}
                        </v-btn>
                    </div>
                </div>
                <div
                    v-else
                    class="continue-empty"
                >
                    <v-icon size="48">
                        mdi-book-open-page-variant-outline
                    </v-icon>
                    <p>{{ t('workbench.pickFirstBook') }}</p>
                    <v-btn
                        to="/discover"
                        variant="text"
                        color="primary"
                    >
                        {{ t('workbench.goFindBook') }}
                    </v-btn>
                </div>
            </v-card>

            <div class="stats-grid">
                <NuxtLink
                    v-for="metric in metrics"
                    :key="metric.label"
                    :to="metric.href"
                    :class="['metric-card', metric.tone]"
                >
                    <span>{{ metric.label }}</span>
                    <strong>{{ metric.value }}</strong>
                    <small>{{ metric.unit }}</small>
                </NuxtLink>
            </div>
        </section>

        <section
            v-if="store.user.is_login"
            class="home-section"
        >
            <div class="section-title-row">
                <div>
                    <p>{{ t('workbench.yourReading') }}</p>
                    <h2>{{ t('navigation.myShelf') }}</h2>
                </div>
                <v-btn
                    to="/user/shelf"
                    variant="text"
                    append-icon="mdi-arrow-right"
                >
                    {{ t('workbench.viewShelf') }}
                </v-btn>
            </div>
            <div class="shelf-shortcuts">
                <NuxtLink
                    v-for="item in shelfShortcuts"
                    :key="item.label"
                    :to="item.href"
                >
                    <v-icon>{{ item.icon }}</v-icon>
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                </NuxtLink>
            </div>
        </section>

        <section class="home-section recent-section">
            <div class="section-title-row">
                <div>
                    <p>{{ t('workbench.libraryUpdate') }}</p>
                    <h2>{{ t('workbench.recentlyAdded') }}</h2>
                </div>
                <v-btn
                    to="/recent"
                    variant="text"
                    append-icon="mdi-arrow-right"
                >
                    {{ t('workbench.viewAll') }}
                </v-btn>
            </div>
            <BookCards
                :books="recentBooks"
                :show-empty-state="!indexPending && recentBooks.length === 0"
            />
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMainStore } from '@/stores/main';

const store = useMainStore();
const { $backend, $alert } = useNuxtApp();
const route = useRoute();
const { t, locale } = useI18n();
const personal = ref({ stats: {}, current_reading_books: [] });
const shelfTotal = ref(0);
let personalLoaded = false;

store.setNavbar(true);

const { data: indexData, pending: indexPending } = useAsyncData('reading-workbench-index', () => $backend('/index'));

const greeting = computed(() => {
    const hour = new Date().getHours();
    const key = hour < 6 ? 'night' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
    return t(`workbench.greeting.${key}`, { name: store.user.nickname || t('workbench.reader') });
});

const stats = computed(() => personal.value.stats || {});
const currentBook = computed(() => personal.value.current_reading_books?.[0] || null);
const heroSummary = computed(() => store.user.is_login
    ? t('workbench.summary', { reading: stats.value.total_reading || 0, done: stats.value.total_read_done || 0 })
    : t('workbench.guestSummary'));
const recentBooks = computed(() => (indexData.value?.new_books || []).slice(0, 12).map(book => ({
    ...book,
    href: `/book/${book.id}`,
})));
const metrics = computed(() => [
    { label: t('workbench.metrics.reading'), value: stats.value.total_reading || 0, unit: t('workbench.units.books'), href: '/user/history', tone: 'tone-blue' },
    { label: t('workbench.metrics.finished'), value: stats.value.total_read_done || 0, unit: t('workbench.units.books'), href: '/user/history?tab=finished', tone: 'tone-peach' },
    { label: t('workbench.metrics.monthFinished'), value: stats.value.month_read_done || 0, unit: t('workbench.units.books'), href: '/user/history?tab=finished', tone: 'tone-mint' },
    { label: t('workbench.metrics.shelf'), value: shelfTotal.value, unit: t('workbench.units.books'), href: '/user/shelf', tone: 'tone-lilac' },
]);
const shelfShortcuts = computed(() => [
    { label: t('workbench.metrics.reading'), value: stats.value.total_reading || 0, href: '/user/history', icon: 'mdi-book-open-page-variant-outline' },
    { label: t('workbench.metrics.finished'), value: stats.value.total_read_done || 0, href: '/user/history?tab=finished', icon: 'mdi-check-circle-outline' },
    { label: t('navigation.libraryCategories'), value: shelfTotal.value, href: '/user/shelf', icon: 'mdi-shape-outline' },
]);
const lastReadLabel = computed(() => {
    const value = currentBook.value?.state?.read_date;
    if (!value) return t('workbench.readyToContinue');
    return t('workbench.lastRead', { date: new Intl.DateTimeFormat(locale.value, { month: 'short', day: 'numeric' }).format(new Date(value)) });
});

function bookAuthors(book) {
    if (Array.isArray(book.authors)) return book.authors.join(' · ');
    return book.author || t('workbench.unknownAuthor');
}

async function loadPersonal() {
    if (!store.user.is_login || personalLoaded) return;
    personalLoaded = true;
    const [statsRsp, shelfRsp] = await Promise.all([
        $backend('/reading/stats'),
        $backend('/shelf'),
    ]);
    if (statsRsp.err === 'ok') personal.value = statsRsp;
    if (shelfRsp.err === 'ok') shelfTotal.value = shelfRsp.total || 0;
}

watch(() => store.user.is_login, loadPersonal, { immediate: true });

onMounted(() => {
    if (route.query.err === 'opds_disabled' && route.query.msg && $alert) {
        $alert('error', route.query.msg);
    }
});
</script>

<style scoped>
.reading-home { display: grid; gap: 32px; padding: 12px 0 36px; }
.home-hero { align-items: center; background: linear-gradient(125deg, rgba(111,139,235,.16), rgba(166,225,207,.16) 52%, rgba(245,190,156,.14)); border: 1px solid rgba(var(--v-border-color), .08); border-radius: 28px; display: flex; justify-content: space-between; overflow: hidden; padding: 34px 38px; position: relative; }
.home-hero::after { background: rgba(255,255,255,.45); border-radius: 50%; content: ''; filter: blur(2px); height: 180px; position: absolute; right: 14%; top: -110px; width: 180px; }
.home-eyebrow,.section-title-row p { color: rgb(var(--v-theme-primary)); font-size: .76rem; font-weight: 700; letter-spacing: .12em; margin: 0 0 6px; text-transform: uppercase; }
.home-hero h1 { font-size: clamp(1.8rem,4vw,3rem); letter-spacing: -.04em; line-height: 1.1; margin: 0 0 12px; }
.home-hero p:not(.home-eyebrow) { color: rgba(var(--v-theme-on-surface), .65); margin: 0; }
.workbench-grid { display: grid; gap: 18px; grid-template-columns: minmax(0,1.55fr) minmax(320px,1fr); }
.workbench-card { border: 1px solid rgba(var(--v-border-color), .08); border-radius: 24px; padding: 26px; }
.continue-card { background: linear-gradient(145deg, rgba(111,139,235,.13), rgba(var(--v-theme-surface),.96)); }
.section-heading,.section-title-row { align-items: flex-start; display: flex; justify-content: space-between; }
.section-heading span { color: rgba(var(--v-theme-on-surface),.58); font-size: .8rem; }
.section-heading h2,.section-title-row h2 { font-size: 1.35rem; margin: 4px 0 0; }
.continue-content { align-items: center; display: flex; gap: 22px; margin-top: 22px; }
.continue-cover { border-radius: 12px; flex: 0 0 112px; height: 152px; box-shadow: 0 12px 28px rgba(38,49,77,.16); }
.continue-copy { align-items: flex-start; display: flex; flex-direction: column; gap: 12px; }
.continue-copy p { margin: 0; }.continue-copy span { color: rgba(var(--v-theme-on-surface),.56); font-size: .86rem; }
.continue-empty { align-items: center; color: rgba(var(--v-theme-on-surface),.58); display: flex; flex-direction: column; justify-content: center; min-height: 160px; text-align: center; }
.continue-empty p { margin: 12px 0 0; }
.stats-grid { display: grid; gap: 14px; grid-template-columns: 1fr 1fr; }
.metric-card { border: 1px solid rgba(255,255,255,.7); border-radius: 22px; color: rgb(var(--v-theme-on-surface)); display: grid; min-height: 132px; padding: 20px; text-decoration: none; transition: transform .2s ease,box-shadow .2s ease; }
.metric-card:hover { box-shadow: 0 12px 26px rgba(44,57,88,.1); transform: translateY(-2px); }
.metric-card span { color: rgba(var(--v-theme-on-surface),.58); font-size: .78rem; }.metric-card strong { align-self: end; font-size: 2.25rem; line-height: 1; }.metric-card small { color: rgba(var(--v-theme-on-surface),.5); }
.tone-blue{background:linear-gradient(135deg,rgba(211,225,255,.78),rgba(var(--v-theme-surface),.84))}.tone-peach{background:linear-gradient(135deg,rgba(255,225,208,.7),rgba(var(--v-theme-surface),.84))}.tone-mint{background:linear-gradient(135deg,rgba(204,241,229,.72),rgba(var(--v-theme-surface),.84))}.tone-lilac{background:linear-gradient(135deg,rgba(229,218,255,.72),rgba(var(--v-theme-surface),.84))}
.home-section { display: grid; gap: 18px; }.section-title-row { align-items: end; }.section-title-row p { color: rgba(var(--v-theme-on-surface),.46); }.shelf-shortcuts { display: grid; gap: 14px; grid-template-columns: repeat(3,1fr); }.shelf-shortcuts a { align-items: center; background: rgb(var(--v-theme-surface)); border: 1px solid rgba(var(--v-border-color),.1); border-radius: 18px; color: inherit; display: grid; gap: 7px; grid-template-columns: auto 1fr auto; padding: 18px; text-decoration: none; }.shelf-shortcuts strong { font-size: 1.25rem; }
.recent-section { padding-bottom: 24px; }
@media(max-width:960px){.workbench-grid{grid-template-columns:1fr}.home-hero{padding:28px}.stats-grid{grid-template-columns:repeat(4,1fr)}.metric-card{min-height:116px;padding:16px}}
@media(max-width:700px){.reading-home{gap:24px;padding-top:0}.home-hero{align-items:flex-start;border-radius:22px;flex-direction:column;gap:22px;padding:24px}.home-hero .v-btn{width:100%}.stats-grid{grid-template-columns:1fr 1fr}.metric-card{border-radius:18px}.shelf-shortcuts{grid-template-columns:1fr}.continue-content{align-items:flex-start}.continue-cover{flex-basis:88px;height:124px}.section-title-row .v-btn{padding-inline:6px}}
@media(prefers-reduced-motion:reduce){.metric-card{transition:none}}
</style>

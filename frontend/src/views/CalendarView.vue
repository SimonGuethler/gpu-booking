<template>
  <div class="calendar-view page-shell">
    <AppTopbar />

    <main
      class="calendar-main page-main"
      aria-label="GPU-Kalender"
    >
      <div
        class="toolbar surface-panel"
        aria-label="Kalendersteuerung"
      >
        <div class="toolbar-nav">
          <Button
            icon="pi pi-chevron-left"
            severity="secondary"
            outlined
            aria-label="Vorherige Woche"
            @click="week.previousWeek()"
          />
          <Button
            label="Heute"
            severity="secondary"
            outlined
            @click="week.goToday()"
          />
          <Button
            icon="pi pi-chevron-right"
            severity="secondary"
            outlined
            aria-label="Nächste Woche"
            @click="week.nextWeek()"
          />
          <span class="week-copy">
            <small>Ausgewählte Woche</small>
            <span class="week-label">{{ week.weekLabel }}</span>
          </span>
        </div>
        <Button
          label="Neue Buchung"
          icon="pi pi-plus"
          @click="onNewBooking"
        />
      </div>

      <div
        v-if="loading"
        class="loading-state"
      >
        <i class="pi pi-spin pi-spinner" />
        <span>Daten werden geladen…</span>
      </div>

      <div
        v-else-if="servers.length === 0"
        class="empty-state"
      >
        <i class="pi pi-database" />
        <h3>Noch keine Server vorhanden</h3>
        <p>Als Admin kannst du im Admin-Bereich Server und GPUs anlegen.</p>
        <Button
          v-if="authStore.isAdmin"
          label="Zum Admin-Bereich"
          icon="pi pi-cog"
          @click="router.push('/admin/servers')"
        />
      </div>

      <template v-else>
        <Tabs
          v-model:value="activeServerTab"
          class="server-tabs"
          scrollable
        >
          <TabList>
            <Tab
              v-for="server in servers"
              :key="server.id"
              :value="server.id"
              class="server-tab"
            >
              <span class="server-tab-icon"><i class="pi pi-server" /></span>
              <span class="server-tab-copy">
                <strong>{{ server.name }}</strong>
                <small>{{ activeGpuCount(server) }} aktive GPUs</small>
              </span>
              <span
                class="server-tab-dot"
                :class="{ off: !server.active }"
                :title="server.active ? 'Server aktiv' : 'Server inaktiv'"
              />
            </Tab>
          </TabList>
        </Tabs>

        <div class="calendar-surface surface-panel">
          <CalendarGrid
            :week-start="week.weekStart.value"
            :servers="activeServers"
            :bookings="bookings"
            :current-user-id="authStore.user?.id ?? 0"
            @open-create="onOpenCreate"
            @open-edit="onOpenEdit"
          />

          <div
            class="legend"
            aria-label="Kalenderlegende"
          >
            <span class="legend-title">Legende</span>
            <div class="legend-item">
              <span class="legend-block legend-train" />
              Vollbelegung · exklusiv
            </div>
            <div class="legend-item">
              <span class="legend-block legend-dev" />
              Teilbelegung · geteilt
            </div>
            <div class="legend-item">
              <span class="legend-block legend-cpu" />
              CPU · geteilt
            </div>
            <div class="legend-item">
              <span class="legend-block legend-own" />
              Eigene Buchung
            </div>
          </div>
        </div>
      </template>
    </main>

    <BookingDrawer
      v-if="activeServerId !== null"
      :visible="drawerVisible"
      :drawer-mode="drawerMode"
      :create-payload="createPayload"
      :booking="editBooking"
      :active-server-id="activeServerId"
      @close="closeDrawer"
      @saved="refreshBookings"
    />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Booking, Server } from '../api/types'
import { useAuthStore } from '../stores/auth'
import { useBookings } from '../composables/useApi'
import { useWeek } from '../composables/useWeek'
import { useServerData } from '../composables/useServerData'
import type { BookingDraft } from '../calendar/logic'
import AppTopbar from '../components/AppTopbar.vue'
import BookingDrawer from '../components/BookingDrawer.vue'
import CalendarGrid from '../components/CalendarGrid.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const week = useWeek()
const serverData = useServerData()

const servers = computed<Server[]>(() => serverData.servers.value ?? [])
const loading = computed(() => serverData.serversLoading.value)

const bookingsQuery = useBookings(() => week.weekStart.value, () => week.weekEnd.value)
const bookings = computed<Booking[]>(() => bookingsQuery.data.value ?? [])

const activeServerId = ref<number | null>(null)
const activeServers = computed<Server[]>(() => {
  const server = servers.value.find((s) => s.id === activeServerId.value)
  return server ? [server] : []
})

const requestedServerId = computed(() => {
  const raw = route.query.server
  return typeof raw === 'string' ? Number.parseInt(raw, 10) : null
})

watch(
  servers,
  (list) => {
    if (list.length === 0) {
      activeServerId.value = null
      return
    }
    const requested = requestedServerId.value
    if (requested !== null && list.some((s) => s.id === requested)) {
      activeServerId.value = requested
      return
    }
    if (activeServerId.value === null || !list.some((s) => s.id === activeServerId.value)) {
      activeServerId.value = list[0].id
    }
  },
  { immediate: true },
)

const activeServerTab = computed({
  get: () => activeServerId.value ?? 0,
  set: (value: string | number) => onServerTabChange(value),
})

function onServerTabChange(id: number | string): void {
  const value = Number(id)
  activeServerId.value = value
  void router.replace({ query: { ...route.query, server: String(value) } })
}

function activeGpuCount(server: Server): number {
  return server.active ? server.gpus.filter((gpu) => gpu.active).length : 0
}

const drawerVisible = ref(false)
const drawerMode = ref<'create' | 'edit'>('create')
const createPayload = ref<BookingDraft | null>(null)
const editBooking = ref<Booking | null>(null)

function onOpenCreate(payload: BookingDraft): void {
  createPayload.value = payload
  editBooking.value = null
  drawerMode.value = 'create'
  drawerVisible.value = true
}

function onNewBooking(): void {
  createPayload.value = null
  editBooking.value = null
  drawerMode.value = 'create'
  drawerVisible.value = true
}

function onOpenEdit(booking: Booking): void {
  editBooking.value = booking
  createPayload.value = null
  drawerMode.value = 'edit'
  drawerVisible.value = true
}

function closeDrawer(): void {
  drawerVisible.value = false
}

function refreshBookings(): void {
  void bookingsQuery.refetch()
}
</script>

<style scoped>
.calendar-view {
  background: var(--c-bg);
}

.calendar-main {
  flex: 1;
  max-width: 1600px;
  padding-top: 1rem;
  padding-inline: clamp(0.75rem, 2vw, 1.5rem);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding: 0.7rem;
}

.toolbar-nav {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.week-label {
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--c-text);
}

.week-copy {
  display: flex;
  flex-direction: column;
  min-width: 12rem;
  margin-left: 0.45rem;
}

.week-copy small {
  color: var(--c-text-muted);
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.server-tabs {
  margin-bottom: 0.75rem;
}

.server-tabs :deep(.p-tablist-tab-list) {
  gap: 0.5rem;
  padding: 0.5rem;
  border: 1px solid var(--c-border-subtle);
  border-radius: var(--app-radius);
  background: var(--c-bg-elevated);
}

.server-tabs :deep(.p-tab) {
  display: flex;
  min-width: 11rem;
  gap: 0.6rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius-sm);
  background: var(--c-surface);
  color: var(--c-text-muted);
  box-shadow: var(--app-shadow-sm);
  transition: border-color 0.14s ease, background 0.14s ease, color 0.14s ease, transform 0.14s ease;
}

.server-tabs :deep(.p-tab:hover) {
  border-color: var(--c-primary-300);
  color: var(--c-primary-700);
  transform: translateY(-1px);
}

.server-tabs :deep(.p-tab.p-tab-active),
.server-tabs :deep(.p-tab[data-p-active='true']) {
  border-color: var(--c-primary);
  background: var(--c-primary);
  color: var(--c-primary-contrast);
  box-shadow: 0 8px 20px -12px color-mix(in srgb, var(--c-primary) 70%, transparent);
}

.server-tab-icon {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 0.55rem;
  background: var(--c-primary-50);
  color: var(--c-primary-700);
}

.server-tabs :deep(.p-tab.p-tab-active) .server-tab-icon,
.server-tabs :deep(.p-tab[data-p-active='true']) .server-tab-icon {
  background: color-mix(in srgb, var(--c-primary-contrast) 20%, transparent);
  color: var(--c-primary-contrast);
}

.server-tab-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}

.server-tab-copy strong {
  max-width: 8rem;
  overflow: hidden;
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.server-tab-copy small {
  margin-top: 0.15rem;
  color: var(--c-text-muted);
  font-size: 0.66rem;
  font-weight: 500;
}

.server-tabs :deep(.p-tab.p-tab-active) .server-tab-copy small,
.server-tabs :deep(.p-tab[data-p-active='true']) .server-tab-copy small {
  color: color-mix(in srgb, var(--c-primary-contrast) 80%, transparent);
}

.server-tab-dot {
  width: 0.5rem;
  height: 0.5rem;
  flex: 0 0 auto;
  border: 2px solid var(--c-surface);
  border-radius: 999px;
  background: var(--p-green-500);
  box-shadow: 0 0 0 1px var(--p-green-500);
}

.server-tab-dot.off {
  background: var(--p-surface-400);
  box-shadow: 0 0 0 1px var(--p-surface-400);
}

.calendar-surface {
  overflow: hidden;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 1px dashed var(--c-border);
  border-radius: var(--p-content-border-radius);
  padding: 3rem 1rem;
  background: var(--c-surface);
  color: var(--c-text-muted);
  font-size: 0.9rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  border: 1px dashed var(--c-border);
  border-radius: var(--p-content-border-radius);
  padding: 3rem 1rem;
  background: var(--c-surface);
  color: var(--c-text-muted);
  text-align: center;
}

.empty-state i {
  font-size: 2rem;
  color: var(--c-primary);
}

.empty-state h3 {
  margin: 0;
  color: var(--c-text);
}

.empty-state p {
  margin: 0 0 0.5rem;
}

.legend {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
  padding: 0.8rem 1rem;
  border-top: 1px solid var(--c-border-subtle);
  background: var(--c-bg-elevated);
  font-size: 0.75rem;
  color: var(--c-text-muted);
}

.legend-title {
  color: var(--c-text);
  font-weight: 700;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.legend-block {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 4px;
  display: inline-block;
}

.legend-train {
  border: 1px solid var(--booking-train-border);
  background: var(--booking-train-bg);
}

.legend-dev {
  border: 1px solid var(--booking-dev-border);
  background: var(--booking-dev-bg);
}

.legend-cpu {
  border: 1px solid var(--booking-cpu-border);
  background: var(--booking-cpu-bg);
}

.legend-own {
  border: 3px solid var(--c-primary);
  background: var(--c-surface);
}

@media (max-width: 760px) {
  .toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-nav {
    width: 100%;
  }

  .week-copy {
    min-width: 0;
  }

  .toolbar > :deep(.p-button) {
    align-self: flex-end;
  }

  .legend-title {
    flex-basis: 100%;
  }
}
</style>

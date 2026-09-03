<template>
  <div class="overview-view page-shell">
    <AppTopbar />

    <main class="overview-main page-main">
      <header class="page-heading">
        <div>
          <p class="page-eyebrow">
            Resource Center
          </p>
          <h1 class="page-title">
            Guten Tag, {{ authStore.user?.display_name }}
          </h1>
          <p class="page-description">
            Aktuelle Übersicht über verfügbare GPU-Ressourcen und die heutige Auslastung.
          </p>
        </div>
        <Button
          label="Buchung planen"
          icon="pi pi-plus"
          @click="router.push('/calendar')"
        />
      </header>

      <div
        v-if="loading"
        class="state-note"
      >
        <i class="pi pi-spin pi-spinner" />
        <span>Daten werden geladen…</span>
      </div>

      <div
        v-else-if="servers.length === 0"
        class="state-note"
      >
        <i class="pi pi-database" />
        <h3>Keine aktiven Server verfügbar</h3>
        <p v-if="authStore.isAdmin">
          Aktiviere einen Server im Admin-Bereich oder lege dort einen neuen an.
        </p>
        <p v-else>
          Bitte wende dich an einen Admin.
        </p>
        <Button
          v-if="authStore.isAdmin"
          label="Zum Admin-Bereich"
          icon="pi pi-cog"
          @click="router.push('/admin/servers')"
        />
      </div>

      <template v-else>
        <section
          class="stats-grid"
          aria-label="Zusammenfassung"
        >
          <div class="stat-card surface-panel">
            <span class="stat-icon"><i class="pi pi-server" /></span>
            <span class="stat-copy"><strong>{{ activeServerCount }}</strong><small>aktive Server</small></span>
          </div>
          <div class="stat-card surface-panel">
            <span class="stat-icon"><i class="pi pi-microchip" /></span>
            <span class="stat-copy"><strong>{{ activeGpuCount }}</strong><small>verfügbare GPUs</small></span>
          </div>
          <div class="stat-card surface-panel">
            <span class="stat-icon"><i class="pi pi-calendar" /></span>
            <span class="stat-copy"><strong>{{ todayBookings.length }}</strong><small>Buchungen heute</small></span>
          </div>
        </section>

        <div class="section-heading">
          <div>
            <h2>Server</h2>
            <p>Hardware und aktuelle Reservierungen auf einen Blick</p>
          </div>
        </div>

        <div class="server-grid">
          <Card
            v-for="server in servers"
            :key="server.id"
            class="server-card"
          >
            <template #title>
              <div class="server-card-title">
                <span class="server-icon"><i class="pi pi-server" /></span>
                <span class="server-title-copy">
                  <span>{{ server.name }}</span>
                  <small>{{ server.hostname || `${server.gpus.length} GPUs` }}</small>
                </span>
              </div>
            </template>
            <template #content>
              <div class="gpu-chips">
                <Chip
                  v-for="gpu in server.gpus"
                  :key="gpu.id"
                  :label="gpuLabel(gpu)"
                  class="gpu-chip"
                  :class="{ 'chip-inactive': !gpu.active }"
                />
                <span
                  v-if="server.gpus.length === 0"
                  class="text-muted no-gpus"
                >Keine GPUs vorhanden</span>
              </div>

              <div class="today-heading">
                GPU-Belegung heute
              </div>
              <div
                v-if="gpuBookingsFor(server).length === 0"
                class="text-muted today-empty"
              >
                Keine GPU-Buchungen heute – GPU-Zeit ist frei.
              </div>
              <ul
                v-else
                class="today-list"
              >
                <li
                  v-for="booking in gpuBookingsFor(server)"
                  :key="booking.id"
                >
                  <span
                    class="booking-dot"
                    :style="{ background: booking.user.color }"
                  />
                  <span class="booking-time">{{ timeRange(booking) }}</span>
                  <span class="booking-user">{{ booking.user.display_name }}</span>
                  <Tag
                    :value="modeLabel(booking.mode)"
                    class="mode-tag"
                  />
                  <span class="booking-project">{{ booking.project.name }}</span>
                </li>
              </ul>

              <div class="today-heading cpu-heading">
                CPU-Auslastung heute
              </div>
              <div
                v-if="cpuBookingsFor(server).length === 0"
                class="text-muted today-empty"
              >
                Keine CPU-Buchungen heute.
              </div>
              <ul
                v-else
                class="today-list"
              >
                <li
                  v-for="booking in cpuBookingsFor(server)"
                  :key="booking.id"
                >
                  <span
                    class="booking-dot"
                    :style="{ background: booking.user.color }"
                  />
                  <span class="booking-time">{{ timeRange(booking) }}</span>
                  <span class="booking-user">{{ booking.user.display_name }}</span>
                  <Tag
                    value="cpu"
                    class="mode-tag"
                  />
                  <span class="booking-project">{{ booking.project.name }}</span>
                </li>
              </ul>
            </template>
            <template #footer>
              <div class="card-actions">
                <Button
                  label="Kalender öffnen"
                  icon="pi pi-calendar"
                  size="small"
                  severity="secondary"
                  outlined
                  @click="openCalendar(server.id)"
                />
              </div>
            </template>
          </Card>
        </div>

        <Card
          v-if="unassignedCpuBookings.length > 0"
          class="unassigned-cpu-card"
        >
          <template #title>
            <div class="server-card-title">
              <i class="pi pi-exclamation-triangle" />
              <span>CPU-Buchungen ohne Serverzuordnung</span>
            </div>
          </template>
          <template #content>
            <p class="unassigned-copy">
              Diese älteren Buchungen wurden vor der Server-Zuordnung angelegt. Bitte im Kalender öffnen und
              einmal einem Server zuweisen.
            </p>
            <ul class="today-list">
              <li
                v-for="booking in unassignedCpuBookings"
                :key="booking.id"
              >
                <span
                  class="booking-dot"
                  :style="{ background: booking.user.color }"
                />
                <span class="booking-time">{{ timeRange(booking) }}</span>
                <span class="booking-user">{{ booking.user.display_name }}</span>
                <Tag
                  value="cpu"
                  class="mode-tag"
                />
                <span class="booking-project">{{ booking.project.name }}</span>
              </li>
            </ul>
          </template>
        </Card>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chip from 'primevue/chip'
import Tag from 'primevue/tag'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import type { Booking, Gpu, Server } from '../api/types'
import { modeLabel } from '../booking/modes'
import { formatHourRange, parseNaiveUtc } from '../calendar/logic'
import { useBookings } from '../composables/useApi'
import { useServerData } from '../composables/useServerData'
import { useToday } from '../composables/useToday'
import { useAuthStore } from '../stores/auth'
import AppTopbar from '../components/AppTopbar.vue'

const authStore = useAuthStore()
const router = useRouter()
const serverData = useServerData()

const servers = computed<Server[]>(() =>
  (serverData.servers.value ?? []).filter((server) => server.active),
)
const loading = computed(() => serverData.serversLoading.value)

const { todayStart, todayEnd } = useToday()
const todayQuery = useBookings(() => todayStart.value, () => todayEnd.value)
const todayBookings = computed<Booking[]>(() => todayQuery.data.value ?? [])
const unassignedCpuBookings = computed(() =>
  todayBookings.value.filter((booking) => booking.mode === 'cpu' && booking.server_id === null),
)

const activeServerCount = computed(() => servers.value.length)
const activeGpuCount = computed(() =>
  servers.value.reduce(
    (total, server) => total + server.gpus.filter((gpu) => gpu.active).length,
    0,
  ),
)

function gpuBookingsFor(server: Server): Booking[] {
  return todayBookings.value.filter(
    (booking) => booking.mode !== 'cpu' && booking.gpus.some((gpu) => gpu.server_id === server.id),
  )
}

function cpuBookingsFor(server: Server): Booking[] {
  return todayBookings.value.filter(
    (booking) => booking.mode === 'cpu' && booking.server_id === server.id,
  )
}

function gpuLabel(gpu: Gpu): string {
  return gpu.memory_mb ? `${gpu.name} · ${Math.round(gpu.memory_mb / 1024)} GB` : gpu.name
}

function timeRange(booking: Booking): string {
  return formatHourRange(parseNaiveUtc(booking.start_at).getTime(), parseNaiveUtc(booking.end_at).getTime())
}

function openCalendar(serverId: number): void {
  void router.push({ path: '/calendar', query: { server: String(serverId) } })
}
</script>

<style scoped>
.overview-view {
  background: var(--c-bg);
}

.overview-main {
  flex: 1;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.75rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 1rem;
}

.stat-icon,
.server-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 0.75rem;
  background: var(--c-primary-50);
  color: var(--c-primary-700);
}

.stat-icon {
  width: 2.6rem;
  height: 2.6rem;
  font-size: 1.05rem;
}

.stat-copy {
  display: flex;
  flex-direction: column;
}

.stat-copy strong {
  color: var(--c-text);
  font-size: 1.25rem;
  line-height: 1.1;
}

.stat-copy small,
.section-heading p,
.server-title-copy small {
  color: var(--c-text-muted);
  font-size: 0.75rem;
}

.section-heading {
  margin-bottom: 0.8rem;
}

.section-heading h2,
.section-heading p {
  margin: 0;
}

.section-heading h2 {
  color: var(--c-text);
  font-size: 1.05rem;
}

.section-heading p {
  margin-top: 0.2rem;
}

.state-note {
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

.state-note i {
  font-size: 2rem;
  color: var(--c-primary);
}

.state-note h3 {
  margin: 0;
  color: var(--c-text);
}

.state-note p {
  margin: 0 0 0.5rem;
}

.server-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
}

.server-card {
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.server-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px -24px rgb(15 23 42 / 0.28);
}

.server-card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
}

.server-card-title i {
  color: var(--c-primary);
}

.server-icon {
  width: 2.15rem;
  height: 2.15rem;
}

.server-title-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  line-height: 1.25;
}

.server-title-copy > span {
  font-weight: 700;
}

.gpu-chips {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.gpu-chip {
  font-size: 0.8rem;
}

.chip-inactive {
  opacity: 0.55;
}

.no-gpus {
  font-size: 0.8rem;
}

.today-heading {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--c-text);
  margin-bottom: 0.5rem;
}

.today-empty {
  font-size: 0.8rem;
}

.today-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.today-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--c-border-subtle);
  border-radius: var(--app-radius-sm);
  background: var(--c-surface);
}

.booking-dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 999px;
  flex-shrink: 0;
}

.booking-time {
  font-weight: 600;
  color: var(--c-text);
  white-space: nowrap;
}

.booking-user {
  font-weight: 600;
}

.booking-project {
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: auto;
}

.mode-tag {
  flex-shrink: 0;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
}

.cpu-heading {
  margin-top: 1rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--c-border-subtle);
}

.unassigned-cpu-card {
  margin-top: 1rem;
  border-color: var(--c-warning-border);
}

.unassigned-copy {
  margin: 0 0 0.75rem;
  color: var(--c-text-muted);
  font-size: 0.8rem;
}

@media (max-width: 720px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .server-grid {
    grid-template-columns: 1fr;
  }

  .today-list li {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .booking-project {
    flex-basis: 100%;
    margin-left: 1.125rem;
  }
}
</style>

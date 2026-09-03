<template>
  <Toolbar class="topbar">
    <template #start>
      <div
        class="topbar-brand"
        role="link"
        tabindex="0"
        title="Zur Übersicht"
        @click="goHome"
        @keydown.enter="goHome"
      >
        <span class="brand-mark"><i class="pi pi-microchip" /></span>
        <span class="brand-copy">
          <span class="brand-name">GPU Booking</span>
          <span class="brand-subtitle">Resource Center</span>
        </span>
      </div>
    </template>

    <template #center>
      <nav class="topbar-nav">
        <Button
          label="Übersicht"
          icon="pi pi-th-large"
          size="small"
          class="nav-button"
          :severity="isOverview ? 'primary' : 'secondary'"
          :text="!isOverview"
          @click="router.push('/')"
        />
        <Button
          label="Kalender"
          icon="pi pi-calendar"
          size="small"
          class="nav-button"
          :severity="isCalendar ? 'primary' : 'secondary'"
          :text="!isCalendar"
          @click="router.push('/calendar')"
        />
        <Button
          v-if="authStore.isAdmin"
          label="Admin"
          icon="pi pi-cog"
          size="small"
          class="nav-button"
          :severity="isAdminPage ? 'primary' : 'secondary'"
          :text="!isAdminPage"
          @click="router.push('/admin/servers')"
        />
      </nav>
    </template>

    <template #end>
      <div class="topbar-actions">
        <ThemeToggle />
        <div class="user-menu">
          <Avatar
            :label="userInitial"
            shape="circle"
            :style="{ background: userColor, color: 'var(--p-surface-0)' }"
          />
          <span class="user-copy">
            <span class="user-name">{{ authStore.user?.display_name }}</span>
            <span class="user-role">{{ authStore.isAdmin ? 'Administrator' : 'Nutzer' }}</span>
          </span>
        </div>
        <Button
          icon="pi pi-sign-out"
          severity="secondary"
          text
          rounded
          aria-label="Abmelden"
          @click="onLogout"
        />
      </div>
    </template>
  </Toolbar>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Toolbar from 'primevue/toolbar'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import ThemeToggle from './ThemeToggle.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const isAdminPage = computed(() => route.path.startsWith('/admin'))
const isCalendar = computed(() => route.name === 'calendar')
const isOverview = computed(() => route.name === 'overview')
const userColor = computed(() => authStore.user?.color ?? 'var(--c-primary)')
const userInitial = computed(() => authStore.user?.display_name?.slice(0, 1).toUpperCase() ?? '?')

function goHome(): void {
  void router.push('/')
}

async function onLogout(): Promise<void> {
  try {
    await authStore.logout()
  } catch {
    // Die lokale Session wird auch bei einem nicht erreichbaren Backend beendet.
  }
  await router.push('/login')
}
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  border-radius: 0;
  box-shadow: var(--app-shadow-sm);
  padding: 0.625rem clamp(1rem, 3vw, 2rem);
  gap: 1rem;
}

.topbar :deep(.p-toolbar-group-start),
.topbar :deep(.p-toolbar-group-end) {
  display: flex;
  align-items: center;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  cursor: pointer;
  user-select: none;
  border-radius: var(--app-radius-sm);
  padding: 0.25rem 0.5rem;
  margin-left: -0.5rem;
  transition: background 0.12s ease;
}

.topbar-brand:hover {
  background: var(--c-primary-50);
}

.topbar-brand:focus-visible {
  outline: 2px solid var(--c-primary);
  outline-offset: 2px;
}

.brand-mark {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  border: 1px solid var(--c-primary-100);
  border-radius: 0.7rem;
  background: var(--c-primary-50);
  color: var(--c-primary-700);
}

.brand-copy,
.user-copy {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--c-text);
  line-height: 1.15;
}

.brand-subtitle,
.user-role {
  margin-top: 0.12rem;
  color: var(--c-text-muted);
  font-size: 0.68rem;
  line-height: 1.15;
}

.topbar-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem;
  border: 1px solid var(--c-border-subtle);
  border-radius: 0.8rem;
  background: var(--c-bg-elevated);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding-right: 0.4rem;
}

.user-menu :deep(.p-avatar) {
  width: 2rem;
  height: 2rem;
  font-size: 0.78rem;
  font-weight: 700;
}

.user-name {
  max-width: 9rem;
  overflow: hidden;
  color: var(--c-text);
  font-size: 0.78rem;
  font-weight: 650;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .brand-copy,
  .user-copy {
    display: none;
  }

  .topbar {
    gap: 0.5rem;
  }

  .topbar :deep(.p-toolbar-group-center) {
    margin-left: auto;
  }

  .topbar-nav :deep(.p-button-label) {
    display: none;
  }

  .nav-button {
    width: 2.4rem;
    padding-inline: 0;
  }

  .user-menu {
    display: none;
  }
}
</style>

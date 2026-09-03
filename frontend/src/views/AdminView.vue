<template>
  <div class="admin-view page-shell">
    <AppTopbar />

    <main class="admin-main page-main">
      <header class="page-heading">
        <div>
          <p class="page-eyebrow">
            Verwaltung
          </p>
          <h1 class="page-title">
            Administration
          </h1>
          <p class="page-description">
            Server, GPUs, Nutzer und Projekte zentral verwalten.
          </p>
        </div>
      </header>

      <Tabs
        v-model:value="activeTab"
        class="admin-tabs"
      >
        <TabList>
          <Tab value="servers">
            <i class="pi pi-server tab-icon" />
            Server & GPUs
          </Tab>
          <Tab value="users">
            <i class="pi pi-users tab-icon" />
            Nutzer
          </Tab>
          <Tab value="projects">
            <i class="pi pi-folder tab-icon" />
            Projekte
          </Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="servers">
            <div class="panel-toolbar">
              <h2>Server</h2>
              <Button
                label="Server anlegen"
                icon="pi pi-plus"
                size="small"
                @click="showServerDialog(null)"
              />
            </div>

            <div
              v-if="loading.servers"
              class="empty-note"
            >
              <i class="pi pi-spin pi-spinner" />
              &nbsp;Server werden geladen…
            </div>

            <div
              v-else-if="servers.length === 0"
              class="empty-note"
            >
              Noch keine Server vorhanden.
            </div>

            <div
              v-for="server in servers"
              :key="server.id"
              class="server-card"
            >
              <div class="server-head">
                <div class="server-title">
                  <i class="pi pi-server" />
                  <span class="server-name">{{ server.name }}</span>
                  <Tag
                    :class="server.active ? 'tag-aktiv' : 'tag-inaktiv'"
                    :value="server.active ? 'aktiv' : 'inaktiv'"
                    :severity="server.active ? 'success' : 'secondary'"
                  />
                </div>
                <div class="server-actions">
                  <Button
                    icon="pi pi-pencil"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    aria-label="Server bearbeiten"
                    @click="showServerDialog(server)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    aria-label="Server löschen"
                    @click="confirmDeleteServer(server)"
                  />
                </div>
              </div>
              <div
                v-for="gpu in server.gpus"
                :key="gpu.id"
                class="gpu-row"
              >
                <span class="gpu-name">
                  <i class="pi pi-microchip" />
                  {{ gpu.name }}
                </span>
                <span class="gpu-meta">
                  <span v-if="gpu.memory_mb">{{ Math.round(gpu.memory_mb / 1024) }} GB</span>
                  <Tag
                    :class="gpu.active ? 'tag-aktiv' : 'tag-inaktiv'"
                    :value="gpu.active ? 'aktiv' : 'inaktiv'"
                    :severity="gpu.active ? 'success' : 'secondary'"
                  />
                </span>
                <span class="gpu-actions">
                  <Button
                    icon="pi pi-pencil"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    aria-label="GPU bearbeiten"
                    @click="showGpuDialog(server, gpu)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    aria-label="GPU löschen"
                    @click="confirmDeleteGpu(server, gpu)"
                  />
                </span>
              </div>
              <div class="gpu-add">
                <Button
                  label="GPU hinzufügen"
                  icon="pi pi-plus"
                  severity="secondary"
                  outlined
                  size="small"
                  @click="showGpuDialog(server, null)"
                />
              </div>
            </div>
          </TabPanel>

          <TabPanel value="users">
            <div class="panel-toolbar">
              <h2>Nutzer</h2>
              <Button
                label="Nutzer anlegen"
                icon="pi pi-plus"
                size="small"
                @click="showUserDialog(null)"
              />
            </div>
            <div class="user-list">
              <div
                v-if="loading.users"
                class="empty-note"
              >
                <i class="pi pi-spin pi-spinner" />
                &nbsp;Nutzer werden geladen…
              </div>
              <div
                v-for="user in users"
                :key="user.id"
                class="user-row"
              >
                <span
                  class="user-dot"
                  :style="{ background: user.color }"
                />
                <span class="user-name">{{ user.display_name }}</span>
                <Tag
                  :value="user.role === 'admin' ? 'Admin' : 'Nutzer'"
                  :severity="user.role === 'admin' ? 'warn' : 'info'"
                />
                <Tag
                  v-if="!user.active"
                  value="Deaktiviert"
                  severity="secondary"
                />
                <Tag
                  v-else-if="!user.approved"
                  value="Wartet auf Freigabe"
                  severity="danger"
                />
                <span class="user-email">{{ user.email }}</span>
                <span class="user-actions">
                  <Button
                    v-if="user.active && !user.approved"
                    label="Freigeben"
                    icon="pi pi-check"
                    severity="success"
                    text
                    size="small"
                    :loading="saving"
                    @click="approveUser(user)"
                  />
                  <Button
                    :icon="user.active ? 'pi pi-ban' : 'pi pi-check-circle'"
                    :severity="user.active ? 'warn' : 'success'"
                    text
                    rounded
                    size="small"
                    :aria-label="user.active ? 'Konto deaktivieren' : 'Konto aktivieren'"
                    :title="user.active ? 'Konto deaktivieren' : 'Konto aktivieren'"
                    @click="confirmToggleUserActive(user)"
                  />
                  <Button
                    icon="pi pi-pencil"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    aria-label="Nutzer bearbeiten"
                    @click="showUserDialog(user)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    aria-label="Konto löschen"
                    title="Konto löschen"
                    @click="confirmDeleteUser(user)"
                  />
                </span>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="projects">
            <div
              v-if="loading.projects"
              class="empty-note"
            >
              <i class="pi pi-spin pi-spinner" />
              &nbsp;Projekte werden geladen…
            </div>
            <div class="project-list">
              <div
                v-for="project in projects"
                :key="project.id"
                class="project-row"
              >
                <div class="project-info">
                  <span class="project-name">{{ project.name }}</span>
                  <span class="project-members">
                    {{ project.members.length }} Mitglieder
                    <span class="project-owner">(Owner: {{ ownerName(project) }})</span>
                  </span>
                  <Tag
                    :class="project.active ? 'tag-aktiv' : 'tag-inaktiv'"
                    :value="project.active ? 'aktiv' : 'inaktiv'"
                    :severity="project.active ? 'success' : 'secondary'"
                  />
                </div>
                <div class="project-actions">
                  <Button
                    :icon="project.active ? 'pi pi-ban' : 'pi pi-check-circle'"
                    :severity="project.active ? 'warn' : 'success'"
                    text
                    rounded
                    size="small"
                    :aria-label="project.active ? 'Projekt deaktivieren' : 'Projekt aktivieren'"
                    :title="project.active ? 'Projekt deaktivieren' : 'Projekt aktivieren'"
                    @click="confirmToggleProjectActive(project)"
                  />
                  <Button
                    icon="pi pi-pencil"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    aria-label="Projekt bearbeiten"
                    @click="showProjectDialog(project)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    rounded
                    size="small"
                    aria-label="Projekt löschen"
                    @click="confirmDeleteProject(project)"
                  />
                </div>
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>

      <Dialog
        v-model:visible="serverDialog.visible"
        :header="serverDialog.editing ? 'Server bearbeiten' : 'Server anlegen'"
        :modal="true"
        :style="{ width: 'min(440px, 90vw)' }"
      >
        <div class="dialog-body">
          <div class="field-block">
            <label class="field-label">Name</label>
            <InputText
              v-model="serverDialog.name"
              class="w-full"
              placeholder="z. B. cuda-01"
            />
          </div>
          <div class="field-block">
            <label class="field-label">Hostname (optional)</label>
            <InputText
              v-model="serverDialog.hostname"
              class="w-full"
              placeholder="z. B. cuda-01.example.org"
            />
          </div>
          <div
            v-if="serverDialog.editing"
            class="field-block"
          >
            <div class="toggle-row">
              <span>Server aktiv</span>
              <InputSwitch v-model="serverDialog.active" />
            </div>
          </div>
        </div>
        <template #footer>
          <div class="dialog-actions">
            <Button
              label="Abbrechen"
              severity="secondary"
              outlined
              @click="serverDialog.visible = false"
            />
            <Button
              label="Speichern"
              icon="pi pi-check"
              :loading="saving"
              :disabled="!serverDialog.name.trim()"
              @click="saveServer"
            />
          </div>
        </template>
      </Dialog>

      <Dialog
        v-model:visible="gpuDialog.visible"
        :header="gpuDialog.editing ? 'GPU bearbeiten' : `GPU an ${gpuDialog.serverName} hinzufügen`"
        :modal="true"
        :style="{ width: 'min(440px, 90vw)' }"
      >
        <div class="dialog-body">
          <div class="field-block">
            <label class="field-label">Name</label>
            <InputText
              v-model="gpuDialog.name"
              class="w-full"
              placeholder="z. B. A100-1"
            />
          </div>
          <div class="field-block">
            <label class="field-label">Speicher in GB (optional)</label>
            <InputNumber
              v-model="gpuDialog.memoryMb"
              :min="0"
              class="w-full"
              placeholder="z. B. 40"
            />
          </div>
          <div
            v-if="gpuDialog.editing"
            class="field-block"
          >
            <div class="toggle-row">
              <span>GPU aktiv</span>
              <InputSwitch v-model="gpuDialog.active" />
            </div>
          </div>
        </div>
        <template #footer>
          <div class="dialog-actions">
            <Button
              label="Abbrechen"
              severity="secondary"
              outlined
              @click="gpuDialog.visible = false"
            />
            <Button
              label="Speichern"
              icon="pi pi-check"
              :loading="saving"
              :disabled="!gpuDialog.name.trim()"
              @click="saveGpu"
            />
          </div>
        </template>
      </Dialog>

      <Dialog
        v-model:visible="userDialog.visible"
        :header="userDialog.editing ? 'Nutzer bearbeiten' : 'Nutzer anlegen'"
        :modal="true"
        :style="{ width: 'min(440px, 90vw)' }"
      >
        <div class="dialog-body">
          <div class="field-block">
            <label class="field-label">Anzeigename</label>
            <InputText
              v-model="userDialog.displayName"
              class="w-full"
              autocomplete="name"
            />
          </div>
          <div class="field-block">
            <label class="field-label">E-Mail</label>
            <InputText
              v-model="userDialog.email"
              type="email"
              autocomplete="email"
              class="w-full"
            />
          </div>
          <div class="field-block">
            <label class="field-label">Farbe</label>
            <div class="color-palette">
              <button
                v-for="color in userColors"
                :key="color"
                type="button"
                class="color-swatch"
                :class="{ 'color-swatch-active': userDialog.color === color }"
                :style="{ background: color }"
                :aria-label="`Farbe ${color} wählen`"
                :title="color"
                @click="userDialog.color = color"
              />
            </div>
            <div class="custom-color-row">
              <ColorPicker
                v-model="customUserColor"
                format="hex"
                aria-label="Eigene Farbe auswählen"
              />
              <InputText
                v-model="userDialog.color"
                maxlength="7"
                placeholder="#01adb9"
                :invalid="!isUserColorValid"
                class="color-input"
                @blur="normalizeUserColor"
              />
              <small>Eigene HEX-Farbe</small>
            </div>
          </div>
          <div class="field-block">
            <label class="field-label">{{ userDialog.editing ? 'Neues Passwort (optional)' : 'Passwort (min. 8 Zeichen)' }}</label>
            <Password
              v-model="userDialog.password"
              :feedback="true"
              class="w-full"
              toggle-mask
            />
            <small
              v-if="userDialog.editing"
              class="hint"
            >Leer lassen, um das Passwort nicht zu ändern.</small>
          </div>
          <div class="field-block">
            <label class="field-label">Rolle</label>
            <Select
              v-model="userDialog.role"
              :options="roleOptions"
              option-label="label"
              option-value="value"
              option-disabled="disabled"
              class="w-full"
            />
            <small
              v-if="isEditingLastAdmin"
              class="hint"
            >Der letzte Administrator kann nicht herabgestuft werden.</small>
          </div>
          <div class="field-block">
            <div class="toggle-row">
              <span>Konto aktiv</span>
              <InputSwitch
                v-model="userDialog.active"
                :disabled="isEditingLastAdmin"
              />
            </div>
            <small class="hint">
              Deaktivierte Konten können sich nicht anmelden, ihre Historie bleibt erhalten.
            </small>
          </div>
          <div class="field-block">
            <div class="toggle-row">
              <span>Konto freigegeben</span>
              <InputSwitch
                v-model="userDialog.approved"
                :disabled="isEditingLastAdmin"
              />
            </div>
            <small class="hint">
              Ohne Freigabe ist keine Anmeldung möglich.
            </small>
          </div>
        </div>
        <template #footer>
          <div class="dialog-actions">
            <Button
              label="Abbrechen"
              severity="secondary"
              outlined
              @click="userDialog.visible = false"
            />
            <Button
              label="Speichern"
              icon="pi pi-check"
              :loading="saving"
              :disabled="!userDialog.displayName.trim() || !userDialog.email.trim() || !isUserColorValid || (!userDialog.editing && userDialog.password.length < 8)"
              @click="saveUser"
            />
          </div>
        </template>
      </Dialog>

      <Dialog
        v-model:visible="projectDialog.visible"
        header="Projekt bearbeiten"
        :modal="true"
        :style="{ width: 'min(480px, 90vw)' }"
      >
        <div class="dialog-body">
          <div class="field-block">
            <label class="field-label">Name</label>
            <InputText
              v-model="projectDialog.name"
              class="w-full"
            />
          </div>
          <div class="field-block">
            <label class="field-label">Beschreibung (optional)</label>
            <Textarea
              v-model="projectDialog.description"
              rows="2"
              class="w-full"
            />
          </div>
          <div class="field-block">
            <label class="field-label">Mitglieder</label>
            <MultiSelect
              v-model="projectDialog.memberIds"
              :options="userOptions"
              option-label="label"
              option-value="value"
              filter
              :max-selected-labels="4"
              class="w-full"
            />
            <small class="hint">Der Owner ist immer Mitglied und kann nicht entfernt werden.</small>
          </div>
          <div class="field-block">
            <div class="toggle-row">
              <span>Projekt aktiv</span>
              <InputSwitch v-model="projectDialog.active" />
            </div>
          </div>
        </div>
        <template #footer>
          <div class="dialog-actions">
            <Button
              label="Abbrechen"
              severity="secondary"
              outlined
              @click="projectDialog.visible = false"
            />
            <Button
              label="Speichern"
              icon="pi pi-check"
              :loading="saving"
              :disabled="!projectDialog.name.trim()"
              @click="saveProject"
            />
          </div>
        </template>
      </Dialog>
    </main>

    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import ColorPicker from 'primevue/colorpicker'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Password from 'primevue/password'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

import type { Gpu, Project, Server, User } from '../api/types'
import { ApiRequestError, del, patch, post } from '../api/client'
import { useColors, useInvalidateAll, useUsers } from '../composables/useApi'
import { useServerData } from '../composables/useServerData'
import AppTopbar from '../components/AppTopbar.vue'

type AdminTab = 'servers' | 'users' | 'projects'

const route = useRoute()
const router = useRouter()
const activeTab = computed<AdminTab>({
  get: () => (route.meta.adminTab as AdminTab | undefined) ?? 'servers',
  set: (tab) => {
    void router.push({ name: `admin-${tab}` })
  },
})
const toast = useToast()
const confirm = useConfirm()
const { servers, projects, serversLoading, projectsLoading } = useServerData()
const usersQuery = useUsers()
const users = computed(() => usersQuery.data.value ?? [])
const colorsQuery = useColors()
const userColors = computed(() => colorsQuery.data.value?.length ? colorsQuery.data.value : ['#01adb9'])
const loading = computed(() => ({
  servers: serversLoading.value,
  users: usersQuery.isLoading.value,
  projects: projectsLoading.value,
}))
const invalidateAll = useInvalidateAll()

const saving = ref(false)

function notify(severity: 'success' | 'error', summary: string, detail = ''): void {
  toast.add({ severity, summary, detail, life: 3500 })
}

async function runSaving(action: () => Promise<void>): Promise<boolean> {
  saving.value = true
  try {
    await action()
    invalidateAll()
    return true
  } catch (e) {
    const message =
      e instanceof ApiRequestError ? e.message : e instanceof Error ? e.message : 'Unbekannter Fehler'
    notify('error', 'Aktion fehlgeschlagen', message)
    return false
  } finally {
    saving.value = false
  }
}

const userOptions = computed(() =>
  users.value.map((u) => ({ label: u.display_name, value: u.id })),
)

const serverDialog = reactive({
  visible: false,
  editing: false,
  id: 0,
  name: '',
  hostname: '',
  active: true,
})

const gpuDialog = reactive({
  visible: false,
  editing: false,
  id: 0,
  serverId: 0,
  serverName: '',
  name: '',
  memoryMb: null as number | null,
  active: true,
})

const userDialog = reactive({
  visible: false,
  editing: false,
  id: 0,
  displayName: '',
  email: '',
  password: '',
  role: 'user',
  approved: true,
  active: true,
  color: '#01adb9',
})

const isEditingLastAdmin = computed(() => {
  if (!userDialog.editing) return false
  const editedUser = users.value.find((user) => user.id === userDialog.id)
  return (
    editedUser?.role === 'admin' &&
    editedUser.approved &&
    editedUser.active &&
    users.value.filter((user) => user.role === 'admin' && user.approved && user.active).length === 1
  )
})

const roleOptions = computed(() => [
  { label: 'Nutzer', value: 'user', disabled: isEditingLastAdmin.value },
  { label: 'Admin', value: 'admin', disabled: false },
])

const customUserColor = computed({
  get: () => userDialog.color.replace(/^#/, ''),
  set: (value: string) => {
    userDialog.color = `#${value}`
  },
})
const isUserColorValid = computed(() => /^#[0-9a-f]{6}$/i.test(userDialog.color))

function normalizeUserColor(): void {
  const value = userDialog.color.trim()
  if (/^[0-9a-f]{6}$/i.test(value)) userDialog.color = `#${value}`
}

const projectDialog = reactive({
  visible: false,
  id: 0,
  name: '',
  description: '',
  active: true,
  memberIds: [] as number[],
})

function showServerDialog(server: Server | null): void {
  serverDialog.editing = server !== null
  serverDialog.id = server?.id ?? 0
  serverDialog.name = server?.name ?? ''
  serverDialog.hostname = server?.hostname ?? ''
  serverDialog.active = server?.active ?? true
  serverDialog.visible = true
}

async function saveServer(): Promise<void> {
  const ok = await runSaving(async () => {
    if (serverDialog.editing) {
      await patch(`/servers/${serverDialog.id}`, {
        name: serverDialog.name.trim(),
        hostname: serverDialog.hostname.trim() || null,
        active: serverDialog.active,
      })
      notify('success', 'Server aktualisiert')
    } else {
      await post('/servers', {
        name: serverDialog.name.trim(),
        hostname: serverDialog.hostname.trim() || null,
      })
      notify('success', 'Server angelegt')
    }
  })
  if (ok) serverDialog.visible = false
}

function confirmDeleteServer(server: Server): void {
  confirm.require({
    message: `Server "${server.name}" wirklich löschen? GPUs mit Buchungen werden dabei deaktiviert.`,
    header: 'Server löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      await runSaving(async () => {
        await del(`/servers/${server.id}`)
        notify('success', 'Server gelöscht bzw. deaktiviert')
      })
    },
  })
}

function showGpuDialog(server: Server, gpu: Gpu | null): void {
  gpuDialog.editing = gpu !== null
  gpuDialog.id = gpu?.id ?? 0
  gpuDialog.serverId = server.id
  gpuDialog.serverName = server.name
  gpuDialog.name = gpu?.name ?? ''
  gpuDialog.memoryMb = gpu?.memory_mb ? Math.round(gpu.memory_mb / 1024) : null
  gpuDialog.active = gpu?.active ?? true
  gpuDialog.visible = true
}

async function saveGpu(): Promise<void> {
  const ok = await runSaving(async () => {
    const memoryMb = gpuDialog.memoryMb != null ? Math.round(gpuDialog.memoryMb * 1024) : null
    if (gpuDialog.editing) {
      await patch(`/gpus/${gpuDialog.id}`, {
        name: gpuDialog.name.trim(),
        memory_mb: memoryMb,
        active: gpuDialog.active,
      })
      notify('success', 'GPU aktualisiert')
    } else {
      await post(`/servers/${gpuDialog.serverId}/gpus`, {
        name: gpuDialog.name.trim(),
        memory_mb: memoryMb,
      })
      notify('success', 'GPU angelegt')
    }
  })
  if (ok) gpuDialog.visible = false
}

function confirmDeleteGpu(server: Server, gpu: Gpu): void {
  confirm.require({
    message: `GPU "${gpu.name}" (${server.name}) wirklich löschen?`,
    header: 'GPU löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      await runSaving(async () => {
        await del(`/gpus/${gpu.id}`)
        notify('success', 'GPU gelöscht')
      })
    },
  })
}

function showUserDialog(user: User | null): void {
  userDialog.editing = user !== null
  userDialog.id = user?.id ?? 0
  userDialog.displayName = user?.display_name ?? ''
  userDialog.email = user?.email ?? ''
  userDialog.password = ''
  userDialog.role = user?.role ?? 'user'
  userDialog.approved = user?.approved ?? true
  userDialog.active = user?.active ?? true
  userDialog.color = user?.color ?? userColors.value[0]
  userDialog.visible = true
}

async function saveUser(): Promise<void> {
  const ok = await runSaving(async () => {
    if (userDialog.editing) {
      const payload: Record<string, unknown> = {
        display_name: userDialog.displayName.trim(),
        email: userDialog.email.trim(),
        role: userDialog.role,
        approved: userDialog.approved,
        active: userDialog.active,
        color: userDialog.color,
      }
      if (userDialog.password) payload.password = userDialog.password
      await patch(`/users/${userDialog.id}`, payload)
      notify('success', 'Nutzer aktualisiert')
    } else {
      await post('/users', {
        display_name: userDialog.displayName.trim(),
        email: userDialog.email.trim(),
        password: userDialog.password,
        role: userDialog.role,
        color: userDialog.color,
      })
      notify('success', 'Nutzer angelegt')
    }
  })
  if (ok) userDialog.visible = false
}

async function approveUser(user: User): Promise<void> {
  await runSaving(async () => {
    await patch(`/users/${user.id}`, { approved: true })
    notify('success', `${user.display_name} wurde freigegeben`)
  })
}

function confirmToggleUserActive(user: User): void {
  const action = user.active ? 'deaktivieren' : 'aktivieren'
  confirm.require({
    message: `Konto von ${user.display_name} wirklich ${action}?`,
    header: user.active ? 'Konto deaktivieren' : 'Konto aktivieren',
    icon: user.active ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle',
    acceptLabel: user.active ? 'Deaktivieren' : 'Aktivieren',
    rejectLabel: 'Abbrechen',
    acceptClass: user.active ? 'p-button-warn' : 'p-button-success',
    accept: async () => {
      await runSaving(async () => {
        await patch(`/users/${user.id}`, { active: !user.active })
        notify('success', `Konto ${user.active ? 'deaktiviert' : 'aktiviert'}`)
      })
    },
  })
}

function confirmDeleteUser(user: User): void {
  confirm.require({
    message:
      `Konto von ${user.display_name} endgültig löschen? ` +
      'Alle Buchungen dieses Kontos werden gelöscht. Eigene Projekte werden auf den löschenden Admin übertragen.',
    header: 'Konto löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Endgültig löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      await runSaving(async () => {
        await del(`/users/${user.id}`)
        notify('success', 'Konto gelöscht')
      })
    },
  })
}

function showProjectDialog(project: Project): void {
  projectDialog.id = project.id
  projectDialog.name = project.name
  projectDialog.description = project.description ?? ''
  projectDialog.active = project.active
  projectDialog.memberIds = project.members.map((m) => m.id)
  projectDialog.visible = true
}

function ownerName(project: Project): string {
  return project.members.find((m) => m.id === project.owner_id)?.display_name ?? '–'
}

async function saveProject(): Promise<void> {
  const ok = await runSaving(async () => {
    await patch(`/projects/${projectDialog.id}`, {
      name: projectDialog.name.trim(),
      description: projectDialog.description.trim() || null,
      active: projectDialog.active,
      member_ids: projectDialog.memberIds,
    })
    notify('success', 'Projekt aktualisiert')
  })
  if (ok) projectDialog.visible = false
}

function confirmDeleteProject(project: Project): void {
  confirm.require({
    message: `Projekt "${project.name}" wirklich löschen? Alle Buchungen dieses Projekts werden ebenfalls gelöscht.`,
    header: 'Projekt löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      await runSaving(async () => {
        await del(`/projects/${project.id}`)
        notify('success', 'Projekt gelöscht')
      })
    },
  })
}

function confirmToggleProjectActive(project: Project): void {
  const action = project.active ? 'deaktivieren' : 'aktivieren'
  confirm.require({
    message: `Projekt "${project.name}" wirklich ${action}?`,
    header: project.active ? 'Projekt deaktivieren' : 'Projekt aktivieren',
    icon: project.active ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle',
    acceptLabel: project.active ? 'Deaktivieren' : 'Aktivieren',
    rejectLabel: 'Abbrechen',
    acceptClass: project.active ? 'p-button-warn' : 'p-button-success',
    accept: async () => {
      await runSaving(async () => {
        await patch(`/projects/${project.id}`, { active: !project.active })
        notify('success', `Projekt ${project.active ? 'deaktiviert' : 'aktiviert'}`)
      })
    },
  })
}
</script>

<style scoped>
.admin-view {
  background: var(--c-bg);
}

.admin-main {
  flex: 1;
  max-width: 1200px;
}

.admin-tabs {
  overflow: hidden;
  border: 1px solid var(--c-border-subtle);
  border-radius: var(--app-radius-lg);
  background: var(--c-surface);
  box-shadow: var(--app-shadow-sm);
}

.admin-tabs :deep(.p-tablist-tab-list) {
  padding: 0.35rem 0.5rem 0;
  background: var(--c-bg-elevated);
}

.admin-tabs :deep(.p-tabpanels) {
  padding: 1.25rem;
}

.tab-icon {
  margin-right: 0.375rem;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.panel-toolbar h2 {
  font-size: 1rem;
  margin: 0;
  color: var(--c-text);
}

.empty-note {
  font-size: 0.85rem;
  color: var(--c-text-muted);
  padding: 1rem 0;
}

.server-card {
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius);
  background: var(--c-surface);
  margin-bottom: 0.75rem;
  overflow: hidden;
}

.server-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.875rem;
  background: color-mix(in srgb, var(--c-primary-50) 62%, var(--c-surface));
  border-bottom: 1px solid var(--c-border);
}

.server-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.server-name {
  font-weight: 700;
  color: var(--c-text);
}

.server-actions {
  display: flex;
  gap: 0.25rem;
}

.gpu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 0.875rem;
  border-bottom: 1px solid var(--c-border-subtle);
}

.gpu-row:last-of-type {
  border-bottom: none;
}

.gpu-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--c-text);
}

.gpu-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--c-text-muted);
}

.gpu-actions {
  display: flex;
  gap: 0.25rem;
}

.gpu-add {
  padding: 0.5rem 0.875rem;
  border-top: 1px dashed var(--c-border);
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius);
  background: var(--c-surface);
  padding: 0.625rem 0.875rem;
}

.user-dot {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 999px;
}

.user-name {
  font-weight: 600;
}

.user-email {
  font-size: 0.8rem;
  color: var(--c-text-muted);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  margin-left: auto;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius);
  background: var(--c-surface);
  padding: 0.625rem 0.875rem;
  gap: 0.75rem;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.project-name {
  font-weight: 600;
}

.project-members {
  font-size: 0.8rem;
  color: var(--c-text-muted);
}

.project-owner {
  color: var(--c-text-secondary);
}

.project-actions {
  display: flex;
  gap: 0.25rem;
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--c-text);
}

.hint {
  font-size: 0.75rem;
  color: var(--c-text-muted);
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.color-palette {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 0.5rem;
}

.color-swatch {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 999px;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
}

.color-swatch:hover {
  transform: scale(1.08);
}

.color-swatch-active {
  border-color: var(--c-text);
  box-shadow: 0 0 0 2px var(--c-surface) inset;
}

.custom-color-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.custom-color-row :deep(.p-colorpicker-preview) {
  width: 2.45rem;
  height: 2.45rem;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius-sm);
}

.color-input {
  min-width: 0;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}

.custom-color-row small {
  color: var(--c-text-muted);
  font-size: 0.7rem;
  white-space: nowrap;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.tag-aktiv {
  background: var(--c-success);
  color: var(--p-primary-contrast-color);
}

.tag-inaktiv {
  background: var(--c-surface-muted);
  color: var(--c-text-muted);
}

@media (max-width: 640px) {
  .admin-tabs :deep(.p-tab) {
    padding-inline: 0.65rem;
    font-size: 0.78rem;
  }

  .admin-tabs :deep(.p-tabpanels) {
    padding: 0.85rem;
  }

  .user-row,
  .project-row,
  .project-info {
    align-items: flex-start;
  }

  .user-email {
    flex-basis: 100%;
    order: 4;
  }
}
</style>

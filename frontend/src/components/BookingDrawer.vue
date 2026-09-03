<template>
  <Drawer
    v-model:visible="visibleModel"
    position="right"
    class="booking-drawer"
    :style="{ width: 'min(540px, 100vw)' }"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-header-copy">
          <small>{{ isEditMode ? 'Reservierung' : 'Zeitfenster planen' }}</small>
          <span>{{ headerText }}</span>
        </span>
        <span class="drawer-user">
          <span
            class="drawer-user-dot"
            :style="{ background: headerUserColor }"
          />
          <span class="drawer-user-name">{{ headerUserName }}</span>
        </span>
      </div>
    </template>
    <div
      ref="drawerBody"
      class="drawer-body"
    >
      <Message
        v-if="formError"
        severity="error"
        :closable="false"
        class="drawer-error"
      >
        {{ formError }}
      </Message>

      <div class="field-block">
        <label class="field-label">Modus</label>
        <SelectButton
          v-model="mode"
          v-bind="modeAttrs"
          :options="modeOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          class="w-full"
        />
        <small class="hint">{{ modeHint }}</small>
      </div>

      <div class="field-block">
        <div class="field-label-row">
          <label class="field-label">Zeitraum</label>
          <span
            v-if="durationLabel"
            class="duration"
          >{{ durationLabel }}</span>
        </div>
        <div class="time-row">
          <label class="time-field">
            <span>Start</span>
            <DatePicker
              v-model="start"
              v-bind="startAttrs"
              show-time
              show-icon
              fluid
              date-format="dd.mm.yy"
              hour-format="24"
              :step-minute="60"
              placeholder="Start"
            />
          </label>
          <label class="time-field">
            <span>Ende</span>
            <DatePicker
              v-model="end"
              v-bind="endAttrs"
              show-time
              show-icon
              fluid
              date-format="dd.mm.yy"
              hour-format="24"
              :step-minute="60"
              placeholder="Ende"
            />
          </label>
        </div>
        <div
          v-if="!isEditMode || isSeriesEdit"
          class="schedule-choice"
        >
          <label class="field-label">Belegung innerhalb des Zeitraums</label>
          <SelectButton
            v-model="schedule"
            v-bind="scheduleAttrs"
            :options="scheduleOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            class="w-full"
          />
          <div
            v-if="values.schedule === 'daily'"
            class="daily-time-row"
          >
            <label class="time-field">
              <span>Täglich von</span>
              <DatePicker
                v-model="dailyStartPicker"
                v-bind="dailyStartAttrs"
                time-only
                hour-format="24"
                :step-minute="60"
                :manual-input="false"
                show-icon
                fluid
              />
            </label>
            <label class="time-field">
              <span>Bis</span>
              <DatePicker
                v-model="dailyEndPicker"
                v-bind="dailyEndAttrs"
                time-only
                hour-format="24"
                :step-minute="60"
                :manual-input="false"
                show-icon
                fluid
              />
            </label>
          </div>
          <small
            v-if="errors.dailyStart"
            class="field-error"
          >{{ errors.dailyStart }}</small>
          <small
            v-else-if="errors.dailyEnd"
            class="field-error"
          >{{ errors.dailyEnd }}</small>
          <small
            v-if="values.schedule === 'daily'"
            class="hint"
          >
            Pro Kalendertag wird ein Zeitfenster erstellt. Am ersten und letzten Tag gelten
            zusätzlich die oben gewählten Grenzen.
          </small>
        </div>
        <small
          v-if="errors.start"
          class="field-error"
        >{{ errors.start }}</small>
        <small
          v-else-if="errors.end"
          class="field-error"
        >{{ errors.end }}</small>
        <div class="quick-row">
          <Button
            v-for="q in quickSlots"
            :key="q.label"
            size="small"
            severity="secondary"
            outlined
            :label="q.label"
            @click="q.apply()"
          />
        </div>
        <small class="hint">
          Zeiten liegen auf vollen Stunden, Mindestdauer 1 Stunde.
          <template v-if="isAdmin">
            Als Admin gilt keine Dauerbegrenzung.
          </template>
          <template v-else>
            Maximale Dauer für reguläre Nutzer: {{ maxBookingDays }}
            {{ maxBookingDays === 1 ? 'Tag' : 'Tage' }}.
          </template>
        </small>
      </div>

      <div class="field-block">
        <label class="field-label">Projekt</label>
        <div class="project-row">
          <Select
            v-model="projectId"
            v-bind="projectIdAttrs"
            :options="projectOptions"
            option-label="label"
            option-value="value"
            filter
            :show-clear="false"
            placeholder="Projekt wählen…"
            class="w-full"
          >
            <template #option="slotProps">
              <div class="project-option">
                <span>{{ slotProps.option.label }}</span>
                <span class="project-members">{{ slotProps.option.memberCount }} Mitglieder</span>
              </div>
            </template>
          </Select>
          <Button
            icon="pi pi-plus"
            severity="secondary"
            outlined
            aria-label="Neues Projekt"
            title="Neues Projekt anlegen"
            @click="showNewProject = true"
          />
        </div>
        <small
          v-if="errors.projectId"
          class="field-error"
        >{{ errors.projectId }}</small>
        <small class="hint">Buchungen dürfen nur vom Ersteller oder von Admins bearbeitet werden.</small>
      </div>

      <div
        v-if="values.mode !== 'cpu'"
        class="field-block"
      >
        <div class="field-label-row">
          <label class="field-label">GPUs</label>
          <span class="hint">{{ selectedGpuCount }} gewählt</span>
        </div>
        <Message
          v-if="hasLegacyCrossServerGpus"
          severity="warn"
          :closable="false"
          class="legacy-gpu-warning"
        >
          Diese ältere Buchung enthält GPUs anderer Server. Beim Speichern wird sie auf
          {{ activeServer?.name ?? 'den aktiven Server' }} beschränkt.
        </Message>
        <div
          v-if="gpuGroups.length === 0"
          class="empty-note"
        >
          Keine aktiven GPUs vorhanden – bitte einen Admin um neue Server/GPUs bitten.
        </div>
        <div
          v-for="group in gpuGroups"
          :key="group.serverId"
          class="gpu-group"
        >
          <div class="gpu-group-name">
            {{ group.serverName }}
          </div>
          <div class="gpu-grid">
            <label
              v-for="gpu in group.gpus"
              :key="gpu.id"
              class="gpu-chip"
              :class="{
                selected: (values.gpuIds ?? []).includes(gpu.id),
                inactive: !gpu.active,
              }"
            >
              <input
                v-model="gpuIds"
                type="checkbox"
                :value="gpu.id"
                class="gpu-checkbox"
              />
              <span class="gpu-chip-label">{{ gpu.name }}</span>
              <span
                v-if="!gpu.active"
                class="gpu-chip-status"
              >inaktiv</span>
              <span
                v-if="gpu.memory_mb"
                class="gpu-chip-memory"
              >
                {{ Math.round(gpu.memory_mb / 1024) }} GB
              </span>
            </label>
          </div>
        </div>
        <small
          v-if="errors.gpuIds"
          class="field-error"
        >{{ errors.gpuIds }}</small>
      </div>

      <div
        v-else
        class="field-block"
      >
        <label class="field-label">Server</label>
        <div class="locked-server">
          <i class="pi pi-lock" />
          <span>{{ activeServer?.name ?? 'Ausgewählter Kalender-Server' }}</span>
        </div>
        <small class="hint">Der Server wird aus dem geöffneten Kalender übernommen.</small>
      </div>

      <div class="field-block">
        <label class="field-label">Beschreibung (optional)</label>
        <Textarea
          v-model="description"
          v-bind="descriptionAttrs"
          rows="2"
          placeholder="z. B. Vollbelegung für ein YOLO-Training…"
          class="w-full"
        />
      </div>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <div class="footer-left">
          <Button
            v-if="canDelete"
            label="Löschen"
            severity="danger"
            outlined
            icon="pi pi-trash"
            @click="confirmDelete"
          />
        </div>
        <div class="footer-right">
          <Button
            label="Abbrechen"
            severity="secondary"
            outlined
            @click="close"
          />
          <Button
            :label="isEditMode ? 'Speichern' : 'Buchen'"
            icon="pi pi-check"
            :loading="saving"
            :disabled="!meta.valid"
            @click="onSubmit"
          />
        </div>
      </div>
    </template>

    <Dialog
      v-model:visible="showNewProject"
      header="Neues Projekt"
      :modal="true"
      :style="{ width: 'min(480px, 90vw)' }"
    >
      <div class="dialog-body">
        <div class="field-block">
          <label class="field-label">Name</label>
          <InputText
            v-model="newProject.name"
            class="w-full"
            placeholder="z. B. KI-Forschung"
          />
        </div>
        <div class="field-block">
          <label class="field-label">Beschreibung (optional)</label>
          <Textarea
            v-model="newProject.description"
            rows="2"
            class="w-full"
          />
        </div>
        <div class="field-block">
          <label class="field-label">Mitglieder</label>
          <MultiSelect
            v-model="newProject.memberIds"
            :options="userOptions"
            option-label="label"
            option-value="value"
            filter
            :max-selected-labels="4"
            placeholder="Mitglieder wählen…"
            class="w-full"
          />
          <small class="hint">Du bist automatisch Mitglied (Owner) und kannst nicht entfernt werden.</small>
        </div>
      </div>
      <template #footer>
        <div class="dialog-actions">
          <Button
            label="Abbrechen"
            severity="secondary"
            outlined
            @click="showNewProject = false"
          />
          <Button
            label="Anlegen"
            icon="pi pi-plus"
            :loading="creatingProject"
            :disabled="!newProject.name.trim()"
            @click="createProject"
          />
        </div>
      </template>
    </Dialog>

    <ConfirmDialog />
  </Drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { toFormValidator } from '@vee-validate/zod'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useForm } from 'vee-validate'

import type { Booking, BookingConflictDetail, Gpu } from '../api/types'
import { ApiRequestError, del, patch, post } from '../api/client'
import type { BookingFormValues } from '../booking/validation'
import { buildDailyIntervals, createBookingSchema } from '../booking/validation'
import { MODE_LABELS, modeLabel } from '../booking/modes'
import { filterGpuIdsForServer } from '../booking/resources'
import { formatLocalDateTimeRange, toNaiveUtc } from '../calendar/logic'
import type { BookingDraft } from '../calendar/logic'
import { useServerData } from '../composables/useServerData'
import { useAppConfig, useInvalidateAll, useUserDirectory } from '../composables/useApi'
import { useAuthStore } from '../stores/auth'
import { addHours, addMinutes, roundToHour } from '../utils/time'

interface GpuGroup {
  serverId: number
  serverName: string
  gpus: Gpu[]
}

const props = defineProps<{
  visible: boolean
  drawerMode: 'create' | 'edit'
  createPayload?: BookingDraft | null
  booking?: Booking | null
  activeServerId: number
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()
const isAdmin = computed(() => auth.user?.role === 'admin')
const isEditMode = computed(() => props.drawerMode === 'edit')
const isSeriesEdit = computed(() => isEditMode.value && Boolean(props.booking?.series_id))
const canDelete = computed(
  () =>
    isEditMode.value &&
    props.booking !== null &&
    props.booking !== undefined &&
    (isAdmin.value || props.booking.user.id === auth.user?.id),
)
const { servers, projects, saveProject } = useServerData()
const appConfigQuery = useAppConfig()
const maxBookingDays = computed(() => appConfigQuery.data.value?.max_booking_days ?? 7)
const userDirectoryQuery = useUserDirectory()
const users = computed(() => userDirectoryQuery.data.value ?? [])
const invalidateAll = useInvalidateAll()

function notify(severity: 'success' | 'error', summary: string, detail = ''): void {
  toast.add({ severity, summary, detail, life: 3500 })
}

const visibleModel = computed({
  get: () => props.visible,
  set: (v: boolean) => {
    if (!v) emit('close')
  },
})

const modeOptions = [
  { label: MODE_LABELS.train, value: 'train' },
  { label: MODE_LABELS.dev, value: 'dev' },
  { label: MODE_LABELS.cpu, value: 'cpu' },
]

const scheduleOptions = [
  { label: 'Durchgehend', value: 'continuous' },
  { label: 'Täglich mit Uhrzeit', value: 'daily' },
]

const modeHint = computed(() => {
  if (values.mode === 'train') {
    return 'Vollbelegung: Die gewählten GPUs sind in diesem Zeitraum exklusiv reserviert.'
  }
  if (values.mode === 'dev') {
    return 'Teilbelegung: Andere können denselben Zeitraum auf den GPUs mitnutzen.'
  }
  return 'CPU-Auslastung: Zeitfenster ohne GPU-Zuordnung auf dem gewählten Server.'
})

function defaultValues(): BookingFormValues {
  const start = roundToHour(addMinutes(new Date(), 60))
  return {
    mode: 'train',
    projectId: null,
    serverId: props.activeServerId,
    gpuIds: [],
    start,
    end: addHours(start, 2),
    schedule: 'continuous',
    dailyStart: '08:00',
    dailyEnd: '16:00',
    description: '',
  }
}

const schema = computed(() =>
  toFormValidator(createBookingSchema(isAdmin.value, maxBookingDays.value)),
)

const { values, errors, meta, handleSubmit, resetForm, setValues, setFieldValue, defineField } =
  useForm<BookingFormValues>({
    validationSchema: schema,
    initialValues: defaultValues(),
  })

const [mode, modeAttrs] = defineField('mode')
const [projectId, projectIdAttrs] = defineField('projectId')
const [gpuIds] = defineField('gpuIds')
const [start, startAttrs] = defineField('start')
const [end, endAttrs] = defineField('end')
const [schedule, scheduleAttrs] = defineField('schedule')
const [dailyStart, dailyStartAttrs] = defineField('dailyStart')
const [dailyEnd, dailyEndAttrs] = defineField('dailyEnd')
const [description, descriptionAttrs] = defineField('description')

function timePickerDate(value: string): Date {
  const [hour, minute] = value.split(':').map(Number)
  return new Date(2000, 0, 1, hour, minute, 0, 0)
}

function timePickerValue(value: Date): string {
  return `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`
}

const dailyStartPicker = computed<Date>({
  get: () => timePickerDate(dailyStart.value),
  set: (value) => {
    dailyStart.value = timePickerValue(value)
  },
})
const dailyEndPicker = computed<Date>({
  get: () => timePickerDate(dailyEnd.value),
  set: (value) => {
    dailyEnd.value = timePickerValue(value)
  },
})

const formError = ref<string | null>(null)
const drawerBody = ref<HTMLElement | null>(null)
const saving = ref(false)
const showNewProject = ref(false)
const creatingProject = ref(false)
const newProject = ref({ name: '', description: '', memberIds: [] as number[] })

const headerText = computed(() =>
  isSeriesEdit.value ? 'Buchungsserie bearbeiten' : isEditMode.value ? 'Buchung bearbeiten' : 'Neue Buchung',
)

const headerUserName = computed(() =>
  isEditMode.value ? (props.booking?.user.display_name ?? '') : (auth.user?.display_name ?? ''),
)

const headerUserColor = computed(() =>
  isEditMode.value ? (props.booking?.user.color ?? 'var(--p-surface-400)') : (auth.user?.color ?? 'var(--p-surface-400)'),
)

const durationLabel = computed(() => {
  if (!start.value || !end.value) return ''
  if ((!isEditMode.value || isSeriesEdit.value) && values.schedule === 'daily') {
    const intervals = buildDailyIntervals(
      start.value,
      end.value,
      values.dailyStart,
      values.dailyEnd,
    )
    const hours = intervals.reduce(
      (total, interval) => total + (interval.end.getTime() - interval.start.getTime()) / 3600_000,
      0,
    )
    if (intervals.length === 0) return ''
    return `${hours} h · ${intervals.length} ${intervals.length === 1 ? 'Tag' : 'Tage'}`
  }
  const hours = (end.value.getTime() - start.value.getTime()) / 3600_000
  if (hours < 0) return ''
  if (hours === 0) return ''
  if (hours % 24 === 0) {
    const days = hours / 24
    return `${days} ${days === 1 ? 'Tag' : 'Tage'}`
  }
  return `${hours} h`
})

function tomorrowAt(hour: number): Date {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(hour, 0, 0, 0)
  return d
}

const quickSlots = computed(() => [
  {
    label: 'Heute · 2 Stunden',
    apply: () => {
      const s = roundToHour(addMinutes(new Date(), 60))
      setQuick(s, addHours(s, 2))
    },
  },
  {
    label: 'Morgen · ganzer Tag',
    apply: () => setQuick(tomorrowAt(9), tomorrowAt(17)),
  },
  {
    label: 'Morgen · Vormittag',
    apply: () => setQuick(tomorrowAt(9), tomorrowAt(12)),
  },
])

function setQuick(start: Date, end: Date): void {
  setFieldValue('start', start)
  setFieldValue('end', end)
}

const projectOptions = computed(() => {
  const current = props.booking?.project
  const options = projects.value
    .filter((project) => project.active || project.id === current?.id)
    .map((project) => ({
      label: project.name,
      value: project.id,
      memberCount: project.members.length,
    }))
  if (current && !options.some((option) => option.value === current.id)) {
    options.unshift({ label: current.name, value: current.id, memberCount: current.members.length })
  }
  return options
})

const userOptions = computed(() =>
  users.value.map((u) => ({
    label: u.display_name,
    value: u.id,
  })),
)

const activeServer = computed(() =>
  servers.value.find((server) => server.id === props.activeServerId),
)

const existingBookingGpuIds = computed(
  () => new Set(isEditMode.value ? (props.booking?.gpus.map((gpu) => gpu.id) ?? []) : []),
)

const gpuGroups = computed<GpuGroup[]>(() =>
  servers.value
    .filter(
      (server) =>
        server.id === props.activeServerId &&
        (server.active || server.gpus.some((gpu) => existingBookingGpuIds.value.has(gpu.id))),
    )
    .map((s) => ({
      serverId: s.id,
      serverName: s.name,
      gpus: s.gpus.filter((gpu) => gpu.active || existingBookingGpuIds.value.has(gpu.id)),
    }))
    .filter((g) => g.gpus.length > 0),
)

const activeServerGpuIds = computed(
  () => new Set(activeServer.value?.gpus.map((gpu) => gpu.id) ?? []),
)
const selectedGpuCount = computed(
  () =>
    filterGpuIdsForServer(
      values.gpuIds ?? [],
      activeServer.value?.gpus ?? [],
      props.activeServerId,
    ).length,
)
const hasLegacyCrossServerGpus = computed(
  () =>
    isEditMode.value &&
    (props.booking?.gpus.some((gpu) => gpu.server_id !== props.activeServerId) ?? false),
)

function isBookingConflictDetail(value: unknown): value is BookingConflictDetail {
  if (!value || typeof value !== 'object') return false
  const detail = value as Record<string, unknown>
  return (
    detail.code === 'booking_conflict' &&
    typeof detail.message === 'string' &&
    typeof detail.start_at === 'string' &&
    typeof detail.end_at === 'string'
  )
}

function bookingConflictMessage(error: ApiRequestError): string {
  if (!isBookingConflictDetail(error.payload)) return error.message
  const range = formatLocalDateTimeRange(error.payload.start_at, error.payload.end_at)
  return `${error.payload.message} Bestehende Buchung: ${range}.`
}

async function showFormError(message: string): Promise<void> {
  formError.value = message
  await nextTick()
  const scrollContainer = drawerBody.value?.closest('.p-drawer-content') as HTMLElement | null
  scrollContainer?.scrollTo({ top: 0, behavior: 'smooth' })
}

async function createProject(): Promise<void> {
  creatingProject.value = true
  try {
    const project = await saveProject({
      name: newProject.value.name.trim(),
      description: newProject.value.description.trim() || undefined,
      member_ids: newProject.value.memberIds,
    })
    setFieldValue('projectId', project.id)
    showNewProject.value = false
    newProject.value = { name: '', description: '', memberIds: [] }
    notify('success', 'Projekt angelegt')
  } catch (e) {
    notify('error', 'Anlegen fehlgeschlagen', e instanceof Error ? e.message : undefined)
  } finally {
    creatingProject.value = false
  }
}

const onSubmit = handleSubmit(async (formValues) => {
  formError.value = null
  saving.value = true
  try {
    const commonPayload = {
      mode: formValues.mode,
      project_id: formValues.projectId!,
      server_id: formValues.mode === 'cpu' ? props.activeServerId : null,
      gpu_ids: formValues.mode === 'cpu' ? [] : formValues.gpuIds,
      description: formValues.description.trim() || undefined,
    }
    const intervals =
      formValues.schedule === 'daily'
        ? buildDailyIntervals(
            formValues.start!,
            formValues.end!,
            formValues.dailyStart,
            formValues.dailyEnd,
          )
        : []
    const seriesPayload = {
      ...commonPayload,
      intervals: intervals.map((interval) => ({
        start_at: toNaiveUtc(interval.start),
        end_at: toNaiveUtc(interval.end),
      })),
      series_start_at: toNaiveUtc(formValues.start!),
      series_end_at: toNaiveUtc(formValues.end!),
      daily_start_hour: Number(formValues.dailyStart.slice(0, 2)),
      daily_end_hour: Number(formValues.dailyEnd.slice(0, 2)),
    }
    if (isSeriesEdit.value && props.booking?.series_id) {
      await patch(`/bookings/series/${props.booking.series_id}`, seriesPayload)
      notify('success', `${intervals.length} Tagesbuchungen aktualisiert`)
    } else if (isEditMode.value && props.booking) {
      await patch(`/bookings/${props.booking.id}`, {
        ...commonPayload,
        start_at: toNaiveUtc(formValues.start!),
        end_at: toNaiveUtc(formValues.end!),
      })
      notify('success', 'Buchung aktualisiert')
    } else if (formValues.schedule === 'daily') {
      await post('/bookings/series', seriesPayload)
      notify('success', `${intervals.length} Tagesbuchungen erstellt`)
    } else {
      await post('/bookings', {
        ...commonPayload,
        start_at: toNaiveUtc(formValues.start!),
        end_at: toNaiveUtc(formValues.end!),
      })
      notify('success', 'Buchung erstellt')
    }
    invalidateAll()
    emit('saved')
    emit('close')
  } catch (e) {
    if (e instanceof ApiRequestError && e.status === 409) {
      await showFormError(bookingConflictMessage(e))
    } else {
      await showFormError(e instanceof Error ? e.message : 'Speichern fehlgeschlagen')
    }
  } finally {
    saving.value = false
  }
})

function confirmDelete(): void {
  if (!props.booking) return
  confirm.require({
    message: isSeriesEdit.value
      ? `Alle Tagesbuchungen der Serie von ${props.booking.user.display_name} wirklich löschen?`
      : `Buchung von ${props.booking.user.display_name} (${modeLabel(props.booking.mode)}) wirklich löschen?`,
    header: isSeriesEdit.value ? 'Buchungsserie löschen' : 'Buchung löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const path = isSeriesEdit.value
          ? `/bookings/series/${props.booking!.series_id}`
          : `/bookings/${props.booking!.id}`
        await del(path)
        notify('success', isSeriesEdit.value ? 'Buchungsserie gelöscht' : 'Buchung gelöscht')
        invalidateAll()
        emit('saved')
        emit('close')
      } catch (e) {
        notify('error', 'Löschen fehlgeschlagen', e instanceof Error ? e.message : undefined)
      }
    },
  })
}

function close(): void {
  emit('close')
}

watch(
  [() => props.visible, () => props.booking, () => props.createPayload],
  () => {
    if (!props.visible) return
    formError.value = null
    if (props.booking) {
      const seriesStart = props.booking.series_start_at
      const seriesEnd = props.booking.series_end_at
      const dailyStartHour = props.booking.daily_start_hour
      const dailyEndHour = props.booking.daily_end_hour
      setValues({
        mode: props.booking.mode,
        projectId: props.booking.project.id,
        serverId: props.activeServerId,
        gpuIds: filterGpuIdsForServer(
          props.booking.gpus.map((gpu) => gpu.id),
          props.booking.gpus,
          props.activeServerId,
        ),
        start: new Date(`${seriesStart ?? props.booking.start_at}Z`),
        end: new Date(`${seriesEnd ?? props.booking.end_at}Z`),
        schedule: props.booking.series_id ? 'daily' : 'continuous',
        dailyStart:
          dailyStartHour == null ? '08:00' : `${String(dailyStartHour).padStart(2, '0')}:00`,
        dailyEnd:
          dailyEndHour == null ? '16:00' : `${String(dailyEndHour).padStart(2, '0')}:00`,
        description: props.booking.description ?? '',
      })
    } else if (props.createPayload) {
      setValues({
        mode: props.createPayload.mode,
        projectId: null,
        serverId: props.activeServerId,
        gpuIds: props.createPayload.gpuIds.filter((gpuId) => activeServerGpuIds.value.has(gpuId)),
        start: props.createPayload.start,
        end: props.createPayload.end,
        schedule: 'continuous',
        dailyStart: '08:00',
        dailyEnd: '16:00',
        description: '',
      })
    } else {
      resetForm({ values: defaultValues() })
    }
  },
)

watch(mode, () => {
  setFieldValue('serverId', props.activeServerId)
})
</script>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--c-text);
}

.drawer-header-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.drawer-header-copy small {
  color: var(--c-primary-600);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.drawer-user {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  background: var(--c-primary-50);
  border: 1px solid var(--c-primary-100);
  border-radius: 999px;
  padding: 0.125rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--c-text);
}

.drawer-user-dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 999px;
}

.drawer-user-name {
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
}

.drawer-error {
  flex: 0 0 auto;
  margin-top: 0.125rem;
}

:deep(.drawer-error .p-message-content) {
  align-items: flex-start;
}

:deep(.drawer-error .p-message-text) {
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
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

.duration {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--c-primary);
}

.field-error {
  font-size: 0.75rem;
  color: var(--c-danger);
}

.locked-server {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.5rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius-sm);
  background: var(--c-bg-elevated);
  color: var(--c-text);
  font-size: 0.85rem;
  font-weight: 600;
}

.locked-server i {
  color: var(--c-text-muted);
}

.legacy-gpu-warning {
  margin-block: 0.125rem;
}

.time-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.time-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.3rem;
}

.time-field > span {
  color: var(--c-text-muted);
  font-size: 0.7rem;
  font-weight: 600;
}

.schedule-choice {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.4rem;
  padding: 0.75rem;
  border: 1px solid var(--c-border-subtle);
  border-radius: var(--app-radius);
  background: var(--c-bg);
}

.daily-time-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.project-row {
  display: flex;
  gap: 0.5rem;
}

.project-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.project-members {
  font-size: 0.7rem;
  color: var(--c-text-secondary);
  white-space: nowrap;
}

.gpu-group {
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius-sm);
  padding: 0.65rem;
  background: var(--c-bg);
}

.gpu-group-name {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--c-text-muted);
  margin-bottom: 0.4rem;
}

.gpu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.375rem;
}

.gpu-chip {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  border: 1px solid var(--c-border);
  border-radius: var(--app-radius-sm);
  padding: 0.4rem 0.55rem;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--c-text);
  background: var(--c-surface);
  transition:
    border-color 0.12s,
    background 0.12s;
}

.gpu-chip:hover {
  border-color: var(--c-primary);
}

.gpu-chip.selected {
  border-color: var(--c-primary);
  background: var(--c-primary-50);
  color: var(--c-primary-700);
}

.gpu-chip.selected .gpu-chip-label {
  font-weight: 600;
  color: var(--c-primary-700);
}

.gpu-chip.selected .gpu-chip-memory {
  color: var(--c-text-muted);
}

.gpu-chip.inactive {
  border-style: dashed;
}

.gpu-chip-status {
  color: var(--c-warning-text);
  font-size: 0.68rem;
  font-weight: 650;
}

.gpu-checkbox {
  accent-color: var(--c-primary);
}

.gpu-chip-memory {
  font-size: 0.7rem;
  color: var(--c-text-muted);
  margin-left: auto;
}

.empty-note {
  font-size: 0.8rem;
  color: var(--c-warning-text);
  background: var(--c-warning-soft);
  border: 1px solid var(--c-warning-border);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

@media (max-width: 480px) {
  .time-row,
  .daily-time-row {
    grid-template-columns: 1fr;
  }

  .drawer-user {
    display: none;
  }
}

.footer-right {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
}

.footer-left {
  margin-right: auto;
}
</style>

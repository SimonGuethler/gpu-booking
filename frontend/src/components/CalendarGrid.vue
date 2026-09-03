<template>
  <div
    ref="scrollEl"
    class="cal-scroll gpu-calendar"
    :class="{ 'is-dragging': dragging }"
    :style="{
      '--cal-day-width': `${dayWidth}px`,
      '--cal-grid-width': `${dayWidth * 7}px`,
      '--cal-label-width': `${CAL_LABEL_WIDTH}px`,
    }"
  >
    <div class="cal-content">
      <div class="cal-header">
        <div class="cal-corner">
          Server / GPU
        </div>
        <div
          v-for="(day, i) in dayLabels"
          :key="i"
          class="cal-day-header"
          :class="{ 'is-today': day.isToday }"
        >
          <div
            class="cal-day-name"
            :class="{ 'is-today': day.isToday }"
          >
            {{ day.label }}
          </div>
          <div class="cal-day-date">
            {{ day.dateLabel }}
          </div>
          <div class="cal-day-scale">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>24:00</span>
          </div>
        </div>
      </div>

      <div
        v-for="row in rows"
        :key="row.key"
        class="cal-row"
        :data-row-key="row.key"
        :class="[
          row.type === 'cpu' ? 'cal-row-cpu' : 'cal-row-gpu',
          { 'is-selected-row': rowsInSelection.has(row.key) },
        ]"
      >
        <div
          class="cal-row-label"
          :class="{ inactive: row.inactive }"
        >
          <template v-if="row.type === 'cpu'">
            <i class="pi pi-calculator" />
            <span>{{ row.name }}</span>
          </template>
          <template v-else>
            <i class="pi pi-microchip" />
            <span>{{ row.name }}</span>
            <span
              v-if="row.memoryMb"
              class="row-memory"
            >
              {{ Math.round(row.memoryMb / 1024) }} GB
            </span>
            <Tag
              v-if="!row.active"
              value="inaktiv"
              severity="secondary"
            />
          </template>
        </div>

        <div
          class="cal-columns"
          :class="{ 'is-cpu': row.type === 'cpu' }"
          @pointerdown.prevent="onPointerDown($event, row)"
        >
          <div
            v-for="col in todayColumns"
            :key="`today-${col.index}`"
            class="cal-col-today"
            :style="{ left: `${col.index * dayWidth}px` }"
          />
          <div
            v-for="h in [4, 8, 12, 16, 20]"
            :key="h"
            class="cal-hour-line"
            :style="{ top: `${(h / 24) * 100}%` }"
          />
          <div
            v-for="i in 6"
            :key="i"
            class="cal-day-line"
            :style="{ left: `${i * dayWidth}px` }"
          />

          <div
            v-if="currentTimeIndicator"
            class="cal-now-line"
            :style="currentTimeIndicator"
          >
            <span class="cal-now-dot" />
          </div>

          <div
            v-for="block in blocksForRow(row)"
            :key="block.key"
            class="cal-block"
            :class="[`mode-${block.mode}`, { own: block.isOwn, train: block.mode === 'train' }]"
            :style="blockStyle(block)"
            :title="tooltip(block)"
            role="button"
            tabindex="0"
            :aria-label="`Buchung von ${block.displayName}: ${modeLabel(block.mode)} – ${block.projectName}`"
            @pointerdown.stop
            @click.stop="emit('open-edit', block.booking)"
            @keydown.enter="emit('open-edit', block.booking)"
          >
            <div class="cal-block-top">
              <span class="cal-block-time">{{ blockTimeLabel(block) }}</span>
              <span class="cal-block-badge">{{ modeLabel(block.mode) }}</span>
            </div>
            <div class="cal-block-project">
              {{ block.projectName }}
            </div>
            <div class="cal-block-user">
              <span class="cal-block-user-dot" />
              {{ block.displayName }}
            </div>
            <div
              v-if="block.booking.description"
              class="cal-block-description"
            >
              {{ block.booking.description }}
            </div>
          </div>

          <div
            v-for="seg in selectionSegments(row)"
            :key="`${row.key}-${seg.dayIndex}-${seg.start}`"
            class="cal-selection"
            :style="selectionStyle(seg)"
          />
        </div>
      </div>
    </div>

    <div
      v-if="dragLabel"
      class="drag-tooltip"
      :style="{ left: `${dragLabel.left}px`, top: `${dragLabel.top}px` }"
    >
      <span class="drag-tooltip-time">{{ dragLabel.text }}</span>
      <span class="drag-tooltip-caption">
        {{ dragLabel.caption }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Tag from 'primevue/tag'

import type { Booking, Server } from '../api/types'
import { modeLabel } from '../booking/modes'
import {
  CAL_DAY_WIDTH,
  bookingMatchesResourceRow,
  calendarBlockPosition,
  formatGermanDate,
  formatGermanDateTime,
  formatGermanTime,
  formatHourRange,
  layoutColumns,
  msFromPointer,
  parseNaiveUtc,
  segmentByDay,
  selectionRowIndexes,
  snapRange,
  startOfWeek,
} from '../calendar/logic'
import { useToday } from '../composables/useToday'
import type { BookingDraft } from '../calendar/logic'

const CAL_LABEL_WIDTH = 190
const MIN_DAY_WIDTH = 140
const MAX_DAY_WIDTH = 190

interface Row {
  key: string
  type: 'gpu' | 'cpu'
  name: string
  serverId: number | null
  gpuId: number | null
  memoryMb: number | null
  active: boolean
  inactive: boolean
  gpuIds: number[]
}

interface CalBlock {
  key: string
  booking: Booking
  mode: 'train' | 'dev' | 'cpu'
  displayName: string
  projectName: string
  isOwn: boolean
  dayIndex: number
  start: number
  end: number
  column: number
  total: number
}

interface SelectionSeg {
  dayIndex: number
  start: number
  end: number
}

interface DragSelection {
  startMs: number
  endMs: number
  gpuIds: Set<number>
  serverId: number | null
  mode: 'train' | 'cpu'
}

const props = defineProps<{
  weekStart: Date
  servers: Server[]
  bookings: Booking[]
  currentUserId: number
}>()

const emit = defineEmits<{
  'open-create': [payload: BookingDraft]
  'open-edit': [booking: Booking]
}>()

const scrollEl = ref<HTMLElement | null>(null)
const dayWidth = ref(CAL_DAY_WIDTH)
const rowsInSelection = ref(new Set<string>())
const selection = ref<DragSelection | null>(null)
const dragLabel = ref<{ left: number; top: number; text: string; caption: string } | null>(null)
const dragging = ref(false)

const rows = computed<Row[]>(() => {
  const result: Row[] = []
  for (const server of props.servers) {
    for (const gpu of server.gpus) {
      const active = server.active && gpu.active
      result.push({
        key: `gpu-${gpu.id}`,
        type: 'gpu',
        name: gpu.name,
        serverId: server.id,
        gpuId: gpu.id,
        memoryMb: gpu.memory_mb,
        active,
        inactive: !active,
        gpuIds: active ? [gpu.id] : [],
      })
    }
    result.push({
      key: `cpu-${server.id}`,
      type: 'cpu',
      name: 'CPU (geteilt)',
      serverId: server.id,
      gpuId: null,
      memoryMb: null,
      active: server.active,
      inactive: !server.active,
      gpuIds: [],
    })
  }
  if (props.bookings.some((booking) => booking.mode === 'cpu' && booking.server_id === null)) {
    result.push({
      key: 'cpu-unassigned',
      type: 'cpu',
      name: 'CPU (ohne Serverzuordnung)',
      serverId: null,
      gpuId: null,
      memoryMb: null,
      active: false,
      inactive: false,
      gpuIds: [],
    })
  }
  return result
})

const now = ref(new Date())
const { todayStart } = useToday()

const dayLabels = computed(() => {
  const labels = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
  const currentDate = now.value
  const todayWeek = startOfWeek(currentDate)
  return labels.map((label, i) => {
    const d = new Date(props.weekStart)
    d.setDate(d.getDate() + i)
    const isToday =
      props.weekStart.getTime() === todayWeek.getTime() &&
      d.getFullYear() === currentDate.getFullYear() &&
      d.getMonth() === currentDate.getMonth() &&
      d.getDate() === currentDate.getDate()
    return {
      label,
      dateLabel: formatGermanDate(d),
      isToday,
    }
  })
})

const todayColumns = computed(() =>
  dayLabels.value
    .map((day, index) => ({ index, isToday: day.isToday }))
    .filter((col) => col.isToday),
)

const currentTimeIndicator = computed<Record<string, string> | null>(() => {
  const today = todayColumns.value[0]
  if (!today) return null
  const currentDate = now.value
  const top = ((currentDate.getHours() * 60 + currentDate.getMinutes()) / (24 * 60)) * 100
  return {
    left: `${today.index * dayWidth.value}px`,
    top: `${top}%`,
    width: `${dayWidth.value}px`,
  }
})

function dayStartMs(dayIndex: number): number {
  const d = new Date(props.weekStart)
  d.setDate(d.getDate() + dayIndex)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

function dayEndMs(dayIndex: number): number {
  const d = new Date(props.weekStart)
  d.setDate(d.getDate() + dayIndex + 1)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

function blocksForRow(row: Row): CalBlock[] {
  const dayBlocks: CalBlock[][] = Array.from({ length: 7 }, () => [])

  for (const booking of props.bookings) {
    const start = parseNaiveUtc(booking.start_at).getTime()
    const end = parseNaiveUtc(booking.end_at).getTime()
    const isOwn = booking.user.id === props.currentUserId

    if (!bookingMatchesResourceRow(row, booking)) continue

    for (let d = 0; d < 7; d++) {
      const segment = segmentByDay(start, end, dayStartMs(d), dayEndMs(d))
      if (!segment) continue
      dayBlocks[d].push({
        key: `${booking.id}-${row.key}-${d}`,
        booking,
        mode: booking.mode,
        displayName: booking.user.display_name,
        projectName: booking.project.name,
        isOwn,
        dayIndex: d,
        start: segment.start,
        end: segment.end,
        column: 0,
        total: 1,
      })
    }
  }

  const result: CalBlock[] = []
  for (let d = 0; d < 7; d++) {
    const blocks = dayBlocks[d]
    const sharedBlocks = blocks.filter((b) => b.mode !== 'train')
    const layouts = layoutColumns(sharedBlocks.map((b) => ({ start: b.start, end: b.end })))
    sharedBlocks.forEach((block, i) => {
      block.column = layouts[i].column
      block.total = layouts[i].total
    })
    result.push(...blocks)
  }
  return result
}

function blockStyle(block: CalBlock): Record<string, string> {
  const dayStart = dayStartMs(block.dayIndex)
  const position = calendarBlockPosition({
    dayIndex: block.dayIndex,
    start: block.start,
    end: block.end,
    dayStart,
    dayEnd: dayEndMs(block.dayIndex),
    dayWidth: dayWidth.value,
    column: block.column,
    total: block.total,
    exclusive: block.mode === 'train',
  })
  const background =
    block.mode === 'train'
      ? 'var(--booking-train-bg)'
      : block.mode === 'dev'
        ? 'var(--booking-dev-bg)'
        : 'var(--booking-cpu-bg)'
  const color =
    block.mode === 'train'
      ? 'var(--booking-train-text)'
      : block.mode === 'dev'
        ? 'var(--booking-dev-text)'
        : 'var(--booking-cpu-text)'
  return {
    top: `${position.topPercent}%`,
    height: `${position.heightPercent}%`,
    left: `${position.leftPx}px`,
    width: `${position.widthPx}px`,
    background,
    color,
    '--booking-color': block.booking.user.color,
  }
}

function blockTimeLabel(block: CalBlock): string {
  const start = new Date(block.start)
  const end = new Date(block.end)
  if (start.toDateString() === end.toDateString()) {
    return `${formatGermanTime(start)}–${formatGermanTime(end)} Uhr`
  }
  return formatHourRange(block.start, block.end)
}

function tooltip(block: CalBlock): string {
  const start = new Date(block.start)
  const end = new Date(block.end)
  const time = `${formatGermanDateTime(start)} – ${formatGermanDateTime(end)}`
  const gpus = block.booking.gpus.map((g) => g.name).join(', ') || 'CPU'
  const description = block.booking.description
    ? `\nBeschreibung: ${block.booking.description}`
    : ''
  return `${block.displayName} (${modeLabel(block.mode)})\n${time}\nGPUs: ${gpus}\nProjekt: ${block.projectName}${description}`
}

function selectionSegments(row: Row): SelectionSeg[] {
  const sel = selection.value
  if (!sel || !rowsInSelection.value.has(row.key)) return []
  const snapped = snapRange(new Date(sel.startMs), new Date(sel.endMs))
  const previewStart = snapped.start.getTime()
  const previewEnd = Math.max(snapped.end.getTime(), previewStart + 3600_000)
  const result: SelectionSeg[] = []
  for (let d = 0; d < 7; d++) {
    const segment = segmentByDay(previewStart, previewEnd, dayStartMs(d), dayEndMs(d))
    if (segment) result.push({ dayIndex: d, start: segment.start, end: segment.end })
  }
  return result
}

function selectionStyle(seg: SelectionSeg): Record<string, string> {
  const dayStart = dayStartMs(seg.dayIndex)
  const position = calendarBlockPosition({
    dayIndex: seg.dayIndex,
    start: seg.start,
    end: seg.end,
    dayStart,
    dayEnd: dayEndMs(seg.dayIndex),
    dayWidth: dayWidth.value,
    column: 0,
    total: 1,
    exclusive: true,
  })
  return {
    top: `${position.topPercent}%`,
    height: `${position.heightPercent}%`,
    left: `${seg.dayIndex * dayWidth.value + 3}px`,
    width: `${dayWidth.value - 6}px`,
  }
}

function columnsRectFor(event: PointerEvent): DOMRect | null {
  const rowEl = (event.target as HTMLElement).closest<HTMLElement>('.cal-row')
  if (!rowEl) return null
  const cols = rowEl.querySelector<HTMLElement>('.cal-columns')
  return cols?.getBoundingClientRect() ?? null
}

let dragStartMs = 0
let dragStartRowKey = ''
let pointer: { clientX: number; clientY: number } | null = null
let autoScrollDir: { x: -1 | 0 | 1; y: -1 | 0 | 1 } = { x: 0, y: 0 }
let rafId: number | null = null
const SCROLL_EDGE = 48
const SCROLL_SPEED = 16

function onPointerDown(event: PointerEvent, row: Row): void {
  if (event.button !== 0) return
  if (!row.active) return
  const rect = columnsRectFor(event)
  if (!rect) return
  event.preventDefault()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  dragStartMs = msFromPointer(x, y, dayWidth.value, rect.height, props.weekStart)
  dragStartRowKey = row.key
  dragging.value = true
  const initialSelection: DragSelection = {
    startMs: dragStartMs,
    endMs: dragStartMs,
    gpuIds: new Set(row.gpuIds),
    serverId: row.type === 'cpu' ? row.serverId : null,
    mode: row.type === 'cpu' ? 'cpu' : 'train',
  }
  selection.value = initialSelection
  applyRowSelection([row], initialSelection)
  pointer = { clientX: event.clientX, clientY: event.clientY }
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerCancel)
  startAutoScroll()
}

function applyRowSelection(selectedRows: Row[], dragSelection: DragSelection): void {
  const gpuIds = new Set(selectedRows.flatMap((row) => row.gpuIds))
  const rowKeys = new Set(selectedRows.map((row) => row.key))

  if (dragSelection.mode === 'train') {
    for (const row of rows.value) {
      if (row.gpuId !== null && gpuIds.has(row.gpuId)) rowKeys.add(row.key)
    }
  }

  rowsInSelection.value = rowKeys
  dragSelection.gpuIds = gpuIds
}

function onPointerMove(event: PointerEvent): void {
  if (!dragging.value) return
  pointer = { clientX: event.clientX, clientY: event.clientY }
  updateDrag()
}

function onPointerUp(): void {
  finishDrag(true)
}

function onPointerCancel(): void {
  finishDrag(false)
}

function finishDrag(commit: boolean): void {
  if (!dragging.value) return
  dragging.value = false
  stopAutoScroll()
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerCancel)
  dragLabel.value = null
  const sel = selection.value
  selection.value = null
  rowsInSelection.value = new Set()
  pointer = null
  dragStartRowKey = ''
  if (!commit || !sel) return

  const snapped = snapRange(new Date(sel.startMs), new Date(sel.endMs))
  let startMs = snapped.start.getTime()
  let endMs = snapped.end.getTime()
  if (endMs - startMs < 3600_000) {
    endMs = startMs + 3600_000
  }
  const gpuIds = Array.from(sel.gpuIds).sort((a, b) => a - b)

  emit('open-create', {
    start: new Date(startMs),
    end: new Date(endMs),
    gpuIds,
    serverId: sel.serverId,
    mode: sel.mode,
  })
}

function updateDrag(): void {
  const sel = selection.value
  const scroll = scrollEl.value
  const p = pointer
  if (!dragging.value || !sel || !scroll || !p) return

  const scrollRect = scroll.getBoundingClientRect()
  autoScrollDir = {
    x: p.clientX < scrollRect.left + SCROLL_EDGE ? -1 : p.clientX > scrollRect.right - SCROLL_EDGE ? 1 : 0,
    y: p.clientY < scrollRect.top + SCROLL_EDGE ? -1 : p.clientY > scrollRect.bottom - SCROLL_EDGE ? 1 : 0,
  }

  const el = document.elementFromPoint(p.clientX, p.clientY)
  const rowEl = el?.closest<HTMLElement>('.cal-row')
  if (!rowEl) return
  const cols = rowEl.querySelector<HTMLElement>('.cal-columns')
  if (!cols) return
  const rect = cols.getBoundingClientRect()
  const x = p.clientX - rect.left
  const y = p.clientY - rect.top
  const currentMs = msFromPointer(x, y, dayWidth.value, rect.height, props.weekStart)
  sel.startMs = Math.min(dragStartMs, currentMs)
  sel.endMs = Math.max(dragStartMs, currentMs)

  const key = rowEl.dataset.rowKey ?? ''
  const startRowIndex = rows.value.findIndex((row) => row.key === dragStartRowKey)
  const currentRowIndex = rows.value.findIndex((row) => row.key === key)
  if (startRowIndex !== -1 && currentRowIndex !== -1) {
    const selectedRows = selectionRowIndexes(startRowIndex, currentRowIndex).map((index) => rows.value[index]).filter((row) => {
      if (!row.active) return false
      return sel.mode === 'cpu' ? row.type === 'cpu' : row.type !== 'cpu'
    })
    applyRowSelection(selectedRows, sel)
  }

  const snapped = snapRange(new Date(sel.startMs), new Date(sel.endMs))
  let endMs = snapped.end.getTime()
  if (endMs - snapped.start.getTime() < 3600_000) endMs = snapped.start.getTime() + 3600_000
  dragLabel.value = {
    left: Math.min(p.clientX + 14, window.innerWidth - 190),
    top: Math.min(p.clientY + 14, window.innerHeight - 64),
    text: formatHourRange(snapped.start.getTime(), endMs),
    caption: sel.mode === 'cpu' ? 'CPU-Zeit' : `${sel.gpuIds.size} GPU${sel.gpuIds.size === 1 ? '' : 's'}`,
  }
}

function autoScrollStep(): void {
  const scroll = scrollEl.value
  if (!scroll) return
  if (autoScrollDir.x !== 0) {
    scroll.scrollLeft += autoScrollDir.x * SCROLL_SPEED
  }
  if (autoScrollDir.y !== 0) {
    scroll.scrollTop += autoScrollDir.y * SCROLL_SPEED
  }
  updateDrag()
  if (dragging.value) {
    rafId = requestAnimationFrame(autoScrollStep)
  }
}

function startAutoScroll(): void {
  stopAutoScroll()
  rafId = requestAnimationFrame(autoScrollStep)
}

function stopAutoScroll(): void {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  autoScrollDir = { x: 0, y: 0 }
}

let resizeObserver: ResizeObserver | null = null
let currentTimeTimer: number | null = null

function syncCurrentTime(): void {
  now.value = new Date()
}

watch(todayStart, syncCurrentTime)

function updateDayWidth(): void {
  const scroll = scrollEl.value
  if (!scroll) return
  const availableWidth = Math.floor((scroll.clientWidth - CAL_LABEL_WIDTH) / 7)
  dayWidth.value = Math.min(MAX_DAY_WIDTH, Math.max(MIN_DAY_WIDTH, availableWidth))
}

onMounted(() => {
  syncCurrentTime()
  currentTimeTimer = window.setInterval(syncCurrentTime, 60_000)
  updateDayWidth()
  resizeObserver = new ResizeObserver(updateDayWidth)
  if (scrollEl.value) resizeObserver.observe(scrollEl.value)
})

onBeforeUnmount(() => {
  if (currentTimeTimer !== null) window.clearInterval(currentTimeTimer)
  resizeObserver?.disconnect()
  stopAutoScroll()
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerCancel)
})
</script>

<style scoped>
.cal-scroll {
  --cal-day-width: 170px;
  --cal-grid-width: 1190px;
  --cal-label-width: 190px;

  overflow: auto;
  max-height: max(28rem, calc(100vh - 21rem));
  background: var(--c-surface);
  scrollbar-width: thin;
  scrollbar-color: var(--c-border) transparent;
}

.cal-content {
  position: relative;
  width: max-content;
  min-width: 100%;
}

.cal-header {
  display: grid;
  grid-template-columns: var(--cal-label-width) repeat(7, var(--cal-day-width));
  position: sticky;
  top: 0;
  z-index: 30;
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  box-shadow: 0 4px 12px -10px rgb(15 23 42 / 0.24);
}

.cal-corner {
  position: sticky;
  left: 0;
  z-index: 32;
  display: flex;
  align-items: center;
  min-width: var(--cal-label-width);
  padding: 0.7rem 0.85rem;
  border-right: 1px solid var(--c-border);
  background: var(--c-surface);
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--c-text-muted);
  white-space: nowrap;
}

.cal-day-header {
  padding: 0.55rem 0.625rem 0.4rem;
  text-align: center;
  border-left: 1px solid var(--c-border);
}

.cal-day-header.is-today {
  background: var(--c-primary-50);
}

.cal-day-name {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--c-text);
}

.cal-day-name.is-today {
  color: var(--c-primary-600);
}

.cal-day-date {
  font-size: 0.7rem;
  color: var(--c-text-muted);
}

.cal-day-header.is-today .cal-day-date {
  color: var(--c-primary-600);
  font-weight: 600;
}

.cal-day-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.55rem;
  color: var(--c-text-secondary);
  margin-top: 0.125rem;
  padding: 0 2px;
}

.cal-row {
  display: grid;
  grid-template-columns: var(--cal-label-width) var(--cal-grid-width);
  border-bottom: 1px solid var(--c-border-subtle);
}

.cal-row-label {
  position: sticky;
  left: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.8rem;
  font-size: 0.85rem;
  background: var(--c-surface);
  border-right: 1px solid var(--c-border);
  min-height: 2rem;
  box-shadow: 6px 0 10px -8px rgb(0 0 0 / 0.18);
  transition: background 0.12s ease, color 0.12s ease;
}

.cal-row.is-selected-row .cal-row-label {
  background: var(--c-primary-100);
  color: var(--c-primary-800);
  box-shadow: inset 3px 0 0 var(--c-primary), 6px 0 10px -8px rgb(0 0 0 / 0.18);
}

.cal-row-label.inactive {
  color: var(--c-text-secondary);
}

.row-memory {
  font-size: 0.7rem;
  color: var(--c-text-muted);
}

.cal-columns {
  position: relative;
  height: 264px;
  background:
    repeating-linear-gradient(
      to bottom,
      var(--c-surface) 0,
      var(--c-surface) calc(66px - 1px),
      var(--c-bg-elevated) calc(66px - 1px),
      var(--c-bg-elevated) 66px
    );
  cursor: crosshair;
  touch-action: none;
  transition: background 0.15s ease;
}

.cal-columns:hover {
  background-color: color-mix(in srgb, var(--c-primary-50) 26%, transparent);
}

.cal-columns.is-cpu {
  background:
    repeating-linear-gradient(
      to bottom,
      var(--c-warning-soft) 0,
      var(--c-warning-soft) calc(66px - 1px),
      var(--c-surface) calc(66px - 1px),
      var(--c-surface) 66px
    );
}

.is-dragging .cal-columns {
  cursor: grabbing;
}

.cal-col-today {
  position: absolute;
  top: 0;
  bottom: 0;
  width: var(--cal-day-width);
  background: color-mix(in srgb, var(--c-primary-100) 55%, transparent);
  z-index: 0;
  pointer-events: none;
}

.cal-hour-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid var(--c-border-subtle);
  pointer-events: none;
}

.cal-day-line {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 1px solid var(--c-border-subtle);
  z-index: 1;
  pointer-events: none;
}

.cal-now-line {
  position: absolute;
  z-index: 2;
  height: 1px;
  background: var(--p-red-400);
  pointer-events: none;
}

.cal-now-dot {
  position: absolute;
  top: -3px;
  left: -3px;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--p-red-500);
}

.cal-block {
  container-name: booking-block;
  container-type: size;
  position: absolute;
  border-radius: var(--p-content-border-radius);
  padding: 0.15rem 0.3rem;
  overflow: hidden;
  cursor: pointer;
  z-index: 3;
  box-shadow: 0 3px 8px -6px rgb(15 23 42 / 0.28);
  font-size: 0.66rem;
  color: var(--c-text);
  border: 1px solid var(--c-border-subtle);
  border-left: 3px solid var(--booking-color);
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-height: 16px;
  transition:
    box-shadow 0.12s ease,
    filter 0.12s ease;
}

.cal-block:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px -12px rgb(15 23 42 / 0.35);
}

.cal-block.mode-train {
  border-color: var(--booking-train-border);
  border-left-color: var(--booking-color);
}

.cal-block.mode-dev {
  border-color: var(--booking-dev-border);
  border-left-color: var(--booking-color);
}

.cal-block.mode-cpu {
  border-color: var(--booking-cpu-border);
  border-left-color: var(--booking-color);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.05);
}

.cal-block.own {
  box-shadow:
    inset 0 0 0 2px var(--c-primary),
    0 3px 8px -6px rgb(15 23 42 / 0.28);
}

.cal-block.own:hover {
  box-shadow:
    inset 0 0 0 2px var(--c-primary),
    0 8px 18px -12px rgb(15 23 42 / 0.35);
}

.cal-block-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
  min-width: 0;
}

.cal-block-time {
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cal-block-badge {
  border-radius: 4px;
  padding: 0 0.25rem;
  font-size: 0.6rem;
  text-transform: uppercase;
  font-weight: 700;
  color: inherit;
  flex-shrink: 0;
}

.mode-train .cal-block-badge {
  background: var(--booking-train-badge);
  color: var(--booking-train-text);
}

.mode-dev .cal-block-badge {
  background: var(--booking-dev-badge);
  color: var(--booking-dev-text);
}

.mode-cpu .cal-block-badge {
  background: var(--booking-cpu-badge);
  color: var(--booking-cpu-text);
}

.cal-block-user,
.cal-block-project,
.cal-block-description {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cal-block-user {
  display: none;
  align-items: center;
  gap: 0.25rem;
  font-weight: 700;
  color: inherit;
}

.cal-block-user-dot {
  width: 0.45rem;
  height: 0.45rem;
  flex: 0 0 auto;
  border: 1px solid rgb(255 255 255 / 0.9);
  border-radius: 999px;
  background: var(--booking-color);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--booking-color) 35%, transparent);
}

.cal-block-project {
  display: none;
  color: inherit;
  font-size: 0.7rem;
  font-weight: 800;
}

.cal-block-description {
  display: none;
  padding-top: 0.1rem;
  border-top: 1px solid color-mix(in srgb, var(--c-text-muted) 18%, transparent);
  color: inherit;
  line-height: 1.25;
  white-space: normal;
}

@container booking-block (min-height: 30px) {
  .cal-block-project {
    display: block;
  }
}

@container booking-block (min-height: 44px) {
  .cal-block-user {
    display: flex;
  }
}

@container booking-block (min-height: 66px) {
  .cal-block-description {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }
}

.cal-selection {
  position: absolute;
  background: color-mix(in srgb, var(--c-primary) 32%, transparent);
  border: 2px solid var(--c-primary-600);
  border-radius: 6px;
  z-index: 4;
  pointer-events: none;
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 0.7),
    0 0 0 3px color-mix(in srgb, var(--c-primary) 16%, transparent);
}

.drag-tooltip {
  position: fixed;
  z-index: 100;
  background: var(--c-surface);
  color: var(--c-text);
  border: 1px solid var(--c-border);
  border-radius: var(--p-content-border-radius);
  padding: 0.375rem 0.625rem;
  font-size: 0.7rem;
  pointer-events: none;
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  box-shadow: 0 4px 16px -2px rgb(0 0 0 / 0.16);
}

.drag-tooltip-time {
  font-weight: 700;
  color: var(--c-primary-600);
}

.drag-tooltip-caption {
  color: var(--c-text-muted);
}
</style>

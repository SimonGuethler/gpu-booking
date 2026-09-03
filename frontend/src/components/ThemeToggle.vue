<template>
  <Button
    :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'"
    severity="secondary"
    text
    rounded
    :aria-label="label"
    :title="label"
    @click="toggleTheme"
  />
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import { computed } from 'vue'

import { useTheme } from '../composables/useTheme'

const { isDark, toggleTheme } = useTheme()
const label = computed(() => (isDark.value ? 'Hellmodus aktivieren' : 'Dunkelmodus aktivieren'))
</script>

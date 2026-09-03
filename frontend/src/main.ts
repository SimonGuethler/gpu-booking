import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import { definePreset } from '@primeuix/themes'
import 'primeicons/primeicons.css'

import App from './App.vue'
import { AUTH_UNAUTHORIZED_EVENT } from './api/client'
import { router } from './router'
import { useAuthStore } from './stores/auth'
import { initializeTheme } from './composables/useTheme'
import './style.css'

initializeTheme()

const AppPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#ecfbfc',
      100: '#d5f5f6',
      200: '#a8e9ec',
      300: '#6fd9de',
      400: '#33c5cc',
      500: '#01adb9',
      600: '#0097a3',
      700: '#007c86',
      800: '#00626a',
      900: '#00484f',
      950: '#003338',
    },
    colorScheme: {
      dark: {
        surface: {
          0: '#ffffff',
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#7a7b83',
          600: '#5f6068',
          700: '#47484f',
          800: '#35363b',
          900: '#2a2b30',
          950: '#212226',
        },
      },
    },
  },
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
window.addEventListener(AUTH_UNAUTHORIZED_EVENT, () => {
  useAuthStore(pinia).clearSession()
  if (router.currentRoute.value.name !== 'login') {
    void router.replace({ name: 'login' })
  }
})
app.use(router)
app.use(VueQueryPlugin)
app.use(PrimeVue, {
  locale: {
    firstDayOfWeek: 1,
    dayNames: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
    dayNamesShort: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
    dayNamesMin: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
    monthNames: [
      'Januar',
      'Februar',
      'März',
      'April',
      'Mai',
      'Juni',
      'Juli',
      'August',
      'September',
      'Oktober',
      'November',
      'Dezember',
    ],
    monthNamesShort: [
      'Jan',
      'Feb',
      'Mär',
      'Apr',
      'Mai',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Okt',
      'Nov',
      'Dez',
    ],
    dateFormat: 'dd.mm.yy',
    today: 'Heute',
    clear: 'Löschen',
    weekHeader: 'KW',
    chooseDate: 'Datum wählen',
    chooseMonth: 'Monat wählen',
    chooseYear: 'Jahr wählen',
    prevMonth: 'Vorheriger Monat',
    nextMonth: 'Nächster Monat',
    prevYear: 'Vorheriges Jahr',
    nextYear: 'Nächstes Jahr',
    prevHour: 'Vorherige Stunde',
    nextHour: 'Nächste Stunde',
    prevMinute: 'Vorherige Minute',
    nextMinute: 'Nächste Minute',
  },
  theme: {
    preset: AppPreset,
    options: {
      darkModeSelector: '.app-dark',
      cssLayer: false,
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)

app.mount('#app')

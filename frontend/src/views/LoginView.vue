<template>
  <div class="login-page">
    <ThemeToggle class="login-theme-toggle" />
    <Card class="login-card">
      <template #title>
        <div class="login-brand">
          <span class="login-brand-mark"><i class="pi pi-microchip" /></span>
          <span>
            <small>Resource Center</small>
            <strong>GPU Booking</strong>
          </span>
        </div>
      </template>
      <template #subtitle>
        <div class="login-intro">
          <span>{{ isRegistering ? 'Konto erstellen' : 'Willkommen zurück' }}</span>
          <small v-if="isRegistering">
            Registriere dich und warte anschließend auf die Freigabe durch einen Admin.
          </small>
          <small v-else>Melde dich an, um Ressourcen zu planen und Buchungen zu verwalten.</small>
        </div>
      </template>
      <template #content>
        <form
          class="p-fluid"
          @submit.prevent="onSubmit"
        >
          <div
            v-if="isRegistering"
            class="field"
          >
            <label for="display-name">Name</label>
            <InputText
              id="display-name"
              v-model="displayName"
              autocomplete="name"
              autofocus
              placeholder="Vor- und Nachname"
            />
          </div>
          <div class="field">
            <label for="email">E-Mail-Adresse</label>
            <InputText
              id="email"
              v-model="email"
              type="email"
              autocomplete="username"
              :autofocus="!isRegistering"
              placeholder="name@unternehmen.de"
            />
          </div>
          <div class="field">
            <label for="password">Passwort</label>
            <Password
              id="password"
              v-model="password"
              :feedback="false"
              toggle-mask
              :autocomplete="isRegistering ? 'new-password' : 'current-password'"
              placeholder="Dein Passwort"
            />
            <small
              v-if="isRegistering"
              class="password-hint"
            >
              Mindestens 8 Zeichen mit Großbuchstabe, Kleinbuchstabe und Zahl.
            </small>
          </div>
          <div
            v-if="isRegistering"
            class="field"
          >
            <label for="password-confirmation">Passwort wiederholen</label>
            <Password
              id="password-confirmation"
              v-model="passwordConfirmation"
              :feedback="false"
              toggle-mask
              autocomplete="new-password"
              placeholder="Passwort erneut eingeben"
            />
          </div>

          <Message
            v-if="error"
            severity="error"
            :closable="false"
            class="login-error"
          >
            {{ error }}
          </Message>
          <Message
            v-if="success"
            severity="success"
            :closable="false"
            class="login-error"
          >
            {{ success }}
          </Message>

          <Button
            type="submit"
            :label="isRegistering ? 'Registrieren' : 'Anmelden'"
            :icon="isRegistering ? 'pi pi-user-plus' : 'pi pi-arrow-right'"
            icon-pos="right"
            :loading="submitting"
            class="login-button"
          />
          <Button
            type="button"
            :label="isRegistering ? 'Zurück zur Anmeldung' : 'Noch kein Konto? Registrieren'"
            severity="secondary"
            text
            class="register-toggle"
            @click="toggleMode"
          />
        </form>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiRequestError, post } from '../api/client'
import { useAuthStore } from '../stores/auth'
import ThemeToggle from '../components/ThemeToggle.vue'

const authStore = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const displayName = ref('')
const passwordConfirmation = ref('')
const error = ref('')
const success = ref('')
const registering = ref(false)
const registrationLoading = ref(false)
const isRegistering = computed(() => registering.value)
const submitting = computed(() => authStore.loading || registrationLoading.value)

function toggleMode(): void {
  registering.value = !registering.value
  error.value = ''
  success.value = ''
  password.value = ''
  passwordConfirmation.value = ''
}

async function onSubmit(): Promise<void> {
  error.value = ''
  success.value = ''
  if (isRegistering.value) {
    if (displayName.value.trim().length < 2 || !email.value.trim() || !password.value) {
      error.value = 'Bitte Name, E-Mail-Adresse und Passwort vollständig eingeben.'
      return
    }
    if (
      password.value.length < 8 ||
      !/\p{Lu}/u.test(password.value) ||
      !/\p{Ll}/u.test(password.value) ||
      !/\d/u.test(password.value)
    ) {
      error.value = 'Das Passwort muss mindestens 8 Zeichen, Groß- und Kleinbuchstaben sowie eine Zahl enthalten.'
      return
    }
    if (password.value !== passwordConfirmation.value) {
      error.value = 'Die Passwörter stimmen nicht überein.'
      return
    }
    registrationLoading.value = true
    try {
      const response = await post<{ message: string }>('/auth/register', {
        display_name: displayName.value.trim(),
        email: email.value.trim(),
        password: password.value,
        password_confirmation: passwordConfirmation.value,
      })
      registering.value = false
      password.value = ''
      passwordConfirmation.value = ''
      success.value = response.message
    } catch (e) {
      error.value = e instanceof ApiRequestError ? e.detail : 'Registrierung fehlgeschlagen.'
    } finally {
      registrationLoading.value = false
    }
    return
  }
  if (!email.value || !password.value) {
    error.value = 'Bitte E-Mail-Adresse und Passwort eingeben.'
    return
  }
  try {
    await authStore.login(email.value.trim(), password.value)
    await router.push('/')
  } catch (e) {
    error.value = e instanceof ApiRequestError ? e.detail : 'Anmeldung fehlgeschlagen.'
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(48rem 32rem at 100% 0, var(--c-primary-100) 0%, transparent 58%),
    radial-gradient(
      42rem 28rem at 0 100%,
      color-mix(in srgb, var(--p-blue-500) 10%, transparent) 0%,
      transparent 58%
    ),
    var(--c-bg);
  padding: 1.5rem;
}

.login-theme-toggle {
  position: absolute;
  top: 1rem;
  right: 1rem;
}

.login-card {
  width: 100%;
  max-width: 440px;
  box-shadow: 0 28px 64px -36px rgb(15 23 42 / 0.38);
}

.login-card :deep(.p-card-body) {
  padding: clamp(1.25rem, 5vw, 2rem);
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.login-brand-mark {
  display: grid;
  width: 2.65rem;
  height: 2.65rem;
  place-items: center;
  border: 1px solid var(--c-primary-100);
  border-radius: 0.85rem;
  background: var(--c-primary-50);
  color: var(--c-primary-700);
  font-size: 1.15rem;
}

.login-brand > span:last-child {
  display: flex;
  flex-direction: column;
}

.login-brand small {
  color: var(--c-primary-600);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.login-brand strong {
  color: var(--c-text);
  font-size: 1.05rem;
}

.login-intro {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1.25rem 0 0.75rem;
}

.login-intro > span {
  color: var(--c-text);
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.login-intro small {
  color: var(--c-text-muted);
  font-size: 0.82rem;
  line-height: 1.5;
}

.field {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field label {
  color: var(--c-text);
  font-size: 0.8rem;
  font-weight: 600;
}

.password-hint {
  color: var(--c-text-muted);
  font-size: 0.72rem;
  line-height: 1.4;
}

.login-error {
  margin-bottom: 1rem;
}

.login-button {
  width: 100%;
  margin-top: 0.25rem;
}

.register-toggle {
  width: 100%;
  margin-top: 0.5rem;
}

</style>

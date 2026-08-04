import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

/**
 * i18n ligero y local de la landing page (ES/EN).
 *
 * Solo la landing necesita dos idiomas; el resto de la app es ES. Este
 * contexto es deliberadamente pequeño: un diccionario tipado por idioma,
 * persistido en localStorage, sin dependencias externas.
 */

export type Lang = "es" | "en"

export const es = {
  nav: {
    features: "Características",
    how: "Cómo funciona",
    privacy: "Privacidad",
    login: "Entrar",
    cta: "Crear cuenta",
  },
  hero: {
    badge: "Self-hosted · PWA · Finanzas del hogar",
    title: "El dinero de tu hogar, en un solo lugar",
    titleAccent: "un solo lugar",
    subtitle:
      "Registra gastos e ingresos en segundos, escanea tus tickets con IA y entiende hacia dónde va tu dinero cada mes. Todo en tu propio servidor.",
    ctaPrimary: "Empezar gratis",
    ctaSecondary: "Ver cómo funciona",
    trust: ["Sin cuentas por miembro", "Tus datos, en tu casa", "Multi-dispositivo"],
  },
  features: {
    kicker: "Lo que hace budget",
    title: "Hecho para el día a día de una familia",
    subtitle:
      "Cada función responde una pregunta real. Nada de tableros que no sirven para la vida cotidiana.",
    items: [
      {
        title: "Entrada rápida",
        desc: "Monto, categoría, cuenta y fecha en menos de 10 segundos, desde el móvil.",
      },
      {
        title: "Escáner de tickets con IA",
        desc: "Saca una foto a tu ticket: extrae, revisa y guarda el gasto sin escribir nada.",
      },
      {
        title: "Recurrentes",
        desc: "La renta, el salario y las suscripciones se registran solos cada mes.",
      },
      {
        title: "Presupuestos",
        desc: "Un límite por categoría con semáforo: verde, ámbar y rojo en la barra.",
      },
      {
        title: "Resumen claro",
        desc: "Balance por cuenta, ingresos vs gastos y a dónde se va el dinero.",
      },
      {
        title: "Un hogar, varias personas",
        desc: "Cada quien su cuenta, todas comparten el mismo hogar con un enlace.",
      },
    ],
  },
  showcase: {
    kicker: "Así se ve",
    title: "Tu dashboard, sin ruido",
    subtitle:
      "Una sola figura protagonista: cuánto tienes. Después, cómo va el mes y hacia dónde se va el dinero.",
    caption: "Vista principal del dashboard",
  },
  how: {
    kicker: "Empieza en minutos",
    title: "Tres pasos y ya están registrando",
    steps: [
      {
        title: "Crea tu hogar",
        desc: "Una cuenta por persona; los demás se unen con un enlace de invitación.",
      },
      {
        title: "Agrega cuentas y categorías",
        desc: "Efectivo, tarjetas y tus categorías con color, listas desde el primer día.",
      },
      {
        title: "Registra y mira el resumen",
        desc: "Anota en segundos y deja que el dashboard responda por ti.",
      },
    ],
  },
  privacy: {
    kicker: "Privacidad de verdad",
    title: "Tus datos viven en tu casa",
    subtitle:
      "budget es self-hosted: el código corre en tu servidor y los datos no tocan la nube de nadie.",
    bullets: [
      "PostgreSQL para tus finanzas, MinIO para tus tickets",
      "Backups con un solo script, verificados de punta a punta",
      "Sin telemetría, sin anuncios, sin terceros",
    ],
  },
  cta: {
    title: "Toma el control hoy",
    subtitle: "Gratis, self-hosted y hecho para tu familia.",
    button: "Crear mi hogar",
  },
  footer: {
    tagline: "El dinero de tu hogar, en un solo lugar",
    madeWith: "Hecho con",
    rights: "Todos los derechos reservados.",
  },
}

export type Dict = typeof es

export const en: Dict = {
  nav: {
    features: "Features",
    how: "How it works",
    privacy: "Privacy",
    login: "Log in",
    cta: "Create account",
  },
  hero: {
    badge: "Self-hosted · PWA · Household finances",
    title: "Your household money, all in one place",
    titleAccent: "all in one place",
    subtitle:
      "Log expenses and income in seconds, scan your receipts with AI and understand where your money goes each month. All on your own server.",
    ctaPrimary: "Get started free",
    ctaSecondary: "See how it works",
    trust: ["One account per member", "Your data, at home", "Multi-device"],
  },
  features: {
    kicker: "What budget does",
    title: "Built for a family's everyday",
    subtitle:
      "Every feature answers a real question. No dashboards that don't serve daily life.",
    items: [
      {
        title: "Quick entry",
        desc: "Amount, category, account and date in under 10 seconds, from your phone.",
      },
      {
        title: "AI receipt scanner",
        desc: "Snap a photo of your receipt: it extracts, you review, and it's logged. No typing.",
      },
      {
        title: "Recurring",
        desc: "Rent, salary and subscriptions record themselves every month.",
      },
      {
        title: "Budgets",
        desc: "A limit per category with a traffic light: green, amber and red in the bar.",
      },
      {
        title: "Clear overview",
        desc: "Balance per account, income vs expenses and where the money goes.",
      },
      {
        title: "One household, many people",
        desc: "Everyone has their own account, all share the same household via a link.",
      },
    ],
  },
  showcase: {
    kicker: "How it looks",
    title: "Your dashboard, without the noise",
    subtitle:
      "One leading figure: how much you have. Then, how the month is going and where the money goes.",
    caption: "Main dashboard view",
  },
  how: {
    kicker: "Start in minutes",
    title: "Three steps and you're logging",
    steps: [
      {
        title: "Create your household",
        desc: "One account per person; everyone else joins with an invitation link.",
      },
      {
        title: "Add accounts and categories",
        desc: "Cash, cards and your color-coded categories, ready from day one.",
      },
      {
        title: "Log and watch the summary",
        desc: "Jot it down in seconds and let the dashboard answer for you.",
      },
    ],
  },
  privacy: {
    kicker: "Real privacy",
    title: "Your data lives at home",
    subtitle:
      "budget is self-hosted: the code runs on your server and the data never touches anyone's cloud.",
    bullets: [
      "PostgreSQL for your finances, MinIO for your receipts",
      "Backups with a single script, verified end to end",
      "No telemetry, no ads, no third parties",
    ],
  },
  cta: {
    title: "Take control today",
    subtitle: "Free, self-hosted and built for your family.",
    button: "Create my household",
  },
  footer: {
    tagline: "Your household money, all in one place",
    madeWith: "Made with",
    rights: "All rights reserved.",
  },
}

const dictionaries: Record<Lang, Dict> = { es, en }

interface LandingI18nContextValue {
  lang: Lang
  t: Dict
  setLang: (lang: Lang) => void
}

const LandingI18nContext = createContext<LandingI18nContextValue | null>(null)

const STORAGE_KEY = "budget-lang"

export function LandingI18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved === "es" || saved === "en") return saved
    } catch {
      /* localStorage no disponible (SSR/privacy mode) */
    }
    return "es"
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      /* noop */
    }
  }, [lang])

  const setLang = (next: Lang) => setLangState(next)

  return (
    <LandingI18nContext.Provider value={{ lang, t: dictionaries[lang], setLang }}>
      {children}
    </LandingI18nContext.Provider>
  )
}

export function useLandingI18n() {
  const ctx = useContext(LandingI18nContext)
  if (!ctx) throw new Error("useLandingI18n must be used within LandingI18nProvider")
  return ctx
}

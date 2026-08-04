import { Link } from "react-router-dom"
import {
  ArrowRight,
  Check,
  Database,
  Globe,
  PieChart,
  RefreshCw,
  ScanLine,
  Server,
  ShieldCheck,
  Target,
  Users,
  Zap,
} from "lucide-react"
import { motion } from "motion/react"

import { BrandMark } from "@/components/BrandMark"
import { useLandingI18n, type Lang } from "@/lib/landing-i18n"
import { springAppear } from "@/lib/springs"

/**
 * Landing pública de budget. Sin sesión, sin app shell.
 *
 * Estructura: hero de marca → características → cómo funciona →
 * privacidad/CTA (banda navy invertida) → footer. El hero es la única
 * superficie con gradiente de marca; la banda final la duplica en navy
 * profundo para cerrar con contraste.
 */

const NAV_ANCHORS = [
  { key: "features", href: "#caracteristicas" },
  { key: "how", href: "#como-funciona" },
  { key: "privacy", href: "#privacidad" },
] as const

function LangToggle() {
  const { lang, setLang } = useLandingI18n()
  const options: { value: Lang; label: string }[] = [
    { value: "es", label: "ES" },
    { value: "en", label: "EN" },
  ]
  return (
    <div
      role="group"
      aria-label="Idioma / Language"
      className="flex rounded-full bg-secondary p-1"
    >
      {options.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => setLang(value)}
          aria-pressed={lang === value}
          className={`relative rounded-full px-3 py-1 text-[13px] font-semibold transition-colors ${
            lang === value ? "text-primary-foreground" : "text-muted-foreground"
          }`}
        >
          {lang === value && (
            <motion.span
              layoutId="lang-pill"
              transition={springAppear}
              className="absolute inset-0 rounded-full bg-primary"
            />
          )}
          <span className="relative">{label}</span>
        </button>
      ))}
    </div>
  )
}

function Nav() {
  const { t } = useLandingI18n()
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/72 backdrop-blur-xl supports-[backdrop-filter]:bg-background/72">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <BrandMark size={28} />

        <nav className="hidden items-center gap-6 md:flex" aria-label="Principal">
          {NAV_ANCHORS.map(({ key, href }) => (
            <a
              key={key}
              href={href}
              className="text-[14px] font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {t.nav[key]}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <LangToggle />
          <Link
            to="/login"
            className="hidden rounded-full px-4 py-2 text-[14px] font-semibold text-foreground transition-colors hover:bg-secondary sm:inline-flex"
          >
            {t.nav.login}
          </Link>
          <Link
            to="/login"
            className="pressable inline-flex h-10 items-center gap-1.5 rounded-full bg-primary px-4 text-[14px] font-semibold text-primary-foreground transition-colors hover:bg-primary/85"
          >
            {t.nav.cta}
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </header>
  )
}

/** Motivo decorativo: barras como las del counter del isotipo. */
function BarMotif({ className }: { className?: string }) {
  const heights = [34, 58, 42, 78, 52, 96, 64]
  return (
    <div
      aria-hidden
      className={`flex items-end gap-1.5 ${className ?? ""}`}
    >
      {heights.map((h, i) => (
        <motion.span
          key={i}
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ ...springAppear, delay: 0.35 + i * 0.06 }}
          style={{ height: `${h}%` }}
          className="w-2 origin-bottom rounded-full bg-white/25"
        />
      ))}
    </div>
  )
}

function BrowserFrame({ caption }: { caption: string }) {
  return (
    <motion.figure
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...springAppear, delay: 0.25 }}
      className="overflow-hidden rounded-3xl border border-white/20 bg-white/10 shadow-2xl backdrop-blur-sm"
    >
      <div className="flex items-center gap-2 border-b border-white/15 px-4 py-3">
        <span className="size-2.5 rounded-full bg-white/40" />
        <span className="size-2.5 rounded-full bg-white/40" />
        <span className="size-2.5 rounded-full bg-white/40" />
        <span className="mx-auto hidden rounded-full bg-white/15 px-4 py-1 text-[12px] font-medium text-white/70 sm:block">
          budget · finanzas del hogar
        </span>
      </div>
      <img
        src="/landing/pantallas.png"
        alt={caption}
        width={1536}
        height={1024}
        className="w-full object-cover"
      />
    </motion.figure>
  )
}

function Hero() {
  const { t } = useLandingI18n()
  const [titleBefore, titleAfter] = t.hero.title.split(t.hero.titleAccent)
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand to-brand-strong text-white">
      {/* Fondo decorativo: motivo de barras + tinte superior */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(60%_50%_at_80%_0%,rgba(255,255,255,0.14),transparent)]" />
        <BarMotif className="absolute right-8 top-1/2 hidden h-40 w-14 -translate-y-1/2 opacity-40 lg:flex" />
        <BarMotif className="absolute left-10 bottom-8 hidden h-24 w-9 opacity-25 xl:flex" />
      </div>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center px-4 pt-16 pb-0 sm:px-6 lg:pt-24">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springAppear}
          className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-4 py-1.5 text-[13px] font-medium text-white/90"
        >
          <span className="size-1.5 rounded-full bg-white" />
          {t.hero.badge}
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springAppear, delay: 0.08 }}
          className="mt-6 max-w-3xl text-center text-[42px] leading-[1.05] font-bold tracking-[-0.03em] sm:text-[56px] lg:text-[68px]"
        >
          {titleBefore}
          <span className="relative inline-block whitespace-nowrap">
            <span className="relative">{t.hero.titleAccent}</span>
            <span
              aria-hidden
              className="absolute inset-x-0 -bottom-1 h-[6px] rounded-full bg-white/25 sm:-bottom-2"
            />
          </span>
          {titleAfter}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springAppear, delay: 0.16 }}
          className="mt-5 max-w-xl text-center text-[16px] leading-relaxed text-white/85 sm:text-[18px]"
        >
          {t.hero.subtitle}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springAppear, delay: 0.24 }}
          className="mt-8 flex flex-col items-center gap-3 sm:flex-row"
        >
          <Link
            to="/login"
            className="pressable inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-white px-6 text-[16px] font-semibold text-brand-strong transition-transform hover:bg-white/90 sm:w-auto"
          >
            {t.hero.ctaPrimary}
            <ArrowRight size={18} />
          </Link>
          <a
            href="#como-funciona"
            className="pressable inline-flex h-12 w-full items-center justify-center gap-2 rounded-full border border-white/30 bg-white/10 px-6 text-[16px] font-semibold text-white transition-colors hover:bg-white/20 sm:w-auto"
          >
            {t.hero.ctaSecondary}
          </a>
        </motion.div>

        <motion.ul
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ ...springAppear, delay: 0.32 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2"
        >
          {t.hero.trust.map((item) => (
            <li
              key={item}
              className="flex items-center gap-1.5 text-[13px] font-medium text-white/75"
            >
              <Check size={14} strokeWidth={3} className="text-white" />
              {item}
            </li>
          ))}
        </motion.ul>

        <div className="mt-12 w-full max-w-4xl lg:-mb-24">
          <BrowserFrame caption={t.showcase.caption} />
        </div>
      </div>
    </section>
  )
}

function SectionKicker({ children }: { children: string }) {
  return (
    <p className="text-[13px] font-semibold tracking-[0.12em] text-primary uppercase">
      {children}
    </p>
  )
}

function SectionTitle({ children }: { children: string }) {
  return (
    <h2 className="mt-3 max-w-2xl text-[32px] leading-tight font-bold tracking-[-0.02em] sm:text-[40px]">
      {children}
    </h2>
  )
}

function SectionIntro({
  kicker,
  title,
  subtitle,
}: {
  kicker: string
  title: string
  subtitle?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.4 }}
      transition={springAppear}
      className="mx-auto max-w-2xl text-center"
    >
      <SectionKicker>{kicker}</SectionKicker>
      <SectionTitle>{title}</SectionTitle>
      {subtitle && (
        <p className="mt-4 text-[16px] leading-relaxed text-muted-foreground">
          {subtitle}
        </p>
      )}
    </motion.div>
  )
}

const FEATURE_ICONS = [Zap, ScanLine, RefreshCw, Target, PieChart, Users]

function Features() {
  const { t } = useLandingI18n()
  return (
    <section
      id="caracteristicas"
      className="scroll-mt-20 bg-background pt-20 pb-24 lg:pt-32 lg:pb-32"
    >
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <SectionIntro
          kicker={t.features.kicker}
          title={t.features.title}
          subtitle={t.features.subtitle}
        />
        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {t.features.items.map((item, i) => {
            const Icon = FEATURE_ICONS[i]
            return (
              <motion.article
                key={item.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ ...springAppear, delay: (i % 3) * 0.07 }}
                className="group rounded-3xl border border-border bg-card p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <span className="flex size-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Icon size={22} />
                </span>
                <h3 className="mt-4 text-[17px] font-semibold tracking-[-0.01em]">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">
                  {item.desc}
                </p>
              </motion.article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  const { t } = useLandingI18n()
  return (
    <section
      id="como-funciona"
      className="scroll-mt-20 border-t border-border bg-card/50 pb-24"
    >
      <div className="mx-auto w-full max-w-6xl px-4 pt-20 sm:px-6 lg:pt-24">
        <SectionIntro kicker={t.how.kicker} title={t.how.title} />
        <ol className="mt-14 grid gap-4 md:grid-cols-3">
          {t.how.steps.map((step, i) => (
            <motion.li
              key={step.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ ...springAppear, delay: i * 0.08 }}
              className="relative rounded-3xl border border-border bg-card p-6 shadow-sm"
            >
              <span className="tnum flex size-9 items-center justify-center rounded-full bg-primary text-[15px] font-bold text-primary-foreground">
                {i + 1}
              </span>
              <h3 className="mt-4 text-[17px] font-semibold tracking-[-0.01em]">
                {step.title}
              </h3>
              <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">
                {step.desc}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  )
}

const PRIVACY_ICONS = [Server, ShieldCheck, Database]

function Privacy() {
  const { t } = useLandingI18n()
  return (
    <section
      id="privacidad"
      className="scroll-mt-20 bg-foreground text-background"
    >
      <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={springAppear}
        >
          <p className="inline-flex items-center gap-2 rounded-full border border-background/20 bg-background/10 px-4 py-1.5 text-[13px] font-semibold text-background/80">
            <ShieldCheck size={14} />
            {t.privacy.kicker}
          </p>
          <h2 className="mt-5 max-w-md text-[32px] leading-tight font-bold tracking-[-0.02em] sm:text-[40px]">
            {t.privacy.title}
          </h2>
          <p className="mt-4 max-w-md text-[16px] leading-relaxed text-background/70">
            {t.privacy.subtitle}
          </p>
          <ul className="mt-8 flex flex-col gap-3">
            {t.privacy.bullets.map((item, i) => {
              const Icon = PRIVACY_ICONS[i]
              return (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-background/10">
                    <Icon size={16} />
                  </span>
                  <span className="text-[14px] font-medium text-background/90">
                    {item}
                  </span>
                </li>
              )
            })}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ ...springAppear, delay: 0.1 }}
          className="flex items-center"
        >
          <div className="w-full rounded-3xl border border-background/15 bg-background/5 p-6 backdrop-blur-sm sm:p-8">
            <div className="flex items-center gap-3">
              <BrandMark size={34} onBrand />
              <div>
                <p className="text-[17px] font-semibold">budget</p>
                <p className="text-[13px] text-background/60">
                  docker compose up -d
                </p>
              </div>
            </div>
            <div className="mt-6 flex flex-col gap-2 font-mono text-[13px]">
              <p className="flex items-center gap-2 text-background/50">
                <Globe size={14} />
                nginx · SPA · PWA
              </p>
              <p className="flex items-center gap-2 text-background/50">
                <Database size={14} />
                PostgreSQL · MinIO
              </p>
              <p className="flex items-center gap-2 text-background/50">
                <Server size={14} />
                FastAPI · JWT
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

function CtaBand() {
  const { t } = useLandingI18n()
  return (
    <section className="border-t border-border bg-background pt-20 pb-28">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={springAppear}
        className="relative mx-auto w-full max-w-6xl overflow-hidden rounded-3xl bg-gradient-to-b from-brand to-brand-strong px-6 py-16 text-center text-white sm:px-12 lg:py-20"
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_60%_at_50%_0%,rgba(255,255,255,0.16),transparent)]" />
        <h2 className="relative mx-auto max-w-xl text-[32px] leading-tight font-bold tracking-[-0.02em] sm:text-[40px]">
          {t.cta.title}
        </h2>
        <p className="relative mt-3 text-[16px] font-medium text-white/85">
          {t.cta.subtitle}
        </p>
        <Link
          to="/login"
          className="pressable relative mt-8 inline-flex h-12 items-center gap-2 rounded-full bg-white px-7 text-[16px] font-semibold text-brand-strong transition-colors hover:bg-white/90"
        >
          {t.cta.button}
          <ArrowRight size={18} />
        </Link>
      </motion.div>
    </section>
  )
}

function Footer() {
  const { t } = useLandingI18n()
  return (
    <footer className="border-t border-border bg-background pb-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-4 px-4 pt-10 sm:px-6">
        <BrandMark size={26} />
        <p className="text-center text-[13px] text-muted-foreground">
          {t.footer.tagline}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
          {NAV_ANCHORS.map(({ key, href }) => (
            <a
              key={key}
              href={href}
              className="text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {t.nav[key]}
            </a>
          ))}
        </div>
        <p className="text-[12px] text-muted-foreground/70">
          © {new Date().getFullYear()} budget · {t.footer.rights}
        </p>
      </div>
    </footer>
  )
}

export function LandingPage() {
  return (
    <div className="min-h-dvh bg-background">
      <Nav />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Privacy />
        <CtaBand />
      </main>
      <Footer />
    </div>
  )
}

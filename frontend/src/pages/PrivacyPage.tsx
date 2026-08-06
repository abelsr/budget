import { Link } from "react-router-dom"

import { BrandMark } from "@/components/BrandMark"

export function PrivacyPage() {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 w-full max-w-3xl items-center justify-between px-4 sm:px-6">
          <Link to="/" aria-label="budget, inicio">
            <BrandMark size={28} />
          </Link>
          <Link
            to="/login"
            className="rounded-full px-4 py-2 text-[14px] font-semibold transition-colors hover:bg-secondary"
          >
            Crear cuenta
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <p className="text-[13px] font-semibold tracking-[0.12em] text-primary uppercase">
          Privacidad
        </p>
        <h1 className="mt-3 text-[36px] leading-tight font-bold tracking-[-0.03em] sm:text-[48px]">
          Tus datos financieros son de tu hogar.
        </h1>
        <p className="mt-5 max-w-2xl text-[17px] leading-relaxed text-muted-foreground">
          budget es una aplicación autoalojada para registrar las finanzas de un hogar.
          Esta página describe los datos que guarda la instancia que usas.
        </p>
        <div className="mt-12 space-y-10 text-[16px] leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-[20px] font-semibold text-foreground">Qué se guarda</h2>
            <p className="mt-2">Tu nombre, correo electrónico y contraseña cifrada, junto con los hogares, cuentas, categorías, movimientos, metas y presupuestos que crees. Si adjuntas comprobantes, también se guardan sus archivos.</p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold text-foreground">Dónde se guarda</h2>
            <p className="mt-2">Los datos viven en la base de datos y el almacenamiento de archivos de la instancia autoalojada. La persona que administra el servidor es responsable de su acceso, copias de seguridad y seguridad física.</p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold text-foreground">Quién puede verlos</h2>
            <p className="mt-2">Las personas que pertenecen al mismo hogar pueden ver la información compartida de ese hogar. Los hogares permanecen aislados entre sí. Las cuentas personales solo se muestran a su titular.</p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold text-foreground">Servicios externos</h2>
            <p className="mt-2">La app no incluye telemetría. Si la persona administradora activa el escáner de tickets, la imagen del comprobante se envía a OpenRouter para analizarla. No hay servicio de correo ni verificación de correo activados.</p>
          </section>
        </div>
      </main>
      <footer className="border-t border-border px-4 py-8 text-center text-[13px] text-muted-foreground">
        <Link to="/" className="font-medium hover:text-foreground">Volver a budget</Link>
      </footer>
    </div>
  )
}

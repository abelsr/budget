import { InviteLink } from "@/components/InviteLink"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"

interface InviteSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Bottom sheet para generar y compartir un link de invitación al hogar. */
export function InviteSheet({ open, onOpenChange }: InviteSheetProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <div className="flex flex-col gap-5 px-5 pb-8">
            <DrawerHeader className="p-0 pt-2">
              <DrawerTitle className="text-center text-[17px] font-semibold">
                Invitar al hogar
              </DrawerTitle>
            </DrawerHeader>

            <p className="text-center text-[14px] leading-snug text-muted-foreground">
              Comparte este link con quien quieras sumar. Al abrirlo podrá crear
              su cuenta y entrar directo a tu hogar.
            </p>

            {/* Abrir el sheet ya es el gesto: el link se genera solo. */}
            <InviteLink autoGenerate />
          </div>
        )}
      </DrawerContent>
    </Drawer>
  )
}

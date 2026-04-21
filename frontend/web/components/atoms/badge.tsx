import { cn } from "@/lib/utils";

type BadgeVariant = "info" | "success" | "danger" | "muted";

export function Badge({ label, variant = "info" }: { label: string; variant?: BadgeVariant }) {
  return (
    <span
      className={cn("rounded-lg px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide", {
        "bg-primary/15 text-primary": variant === "info",
        "bg-emerald-100 text-emerald-700": variant === "success",
        "bg-red-100 text-red-700": variant === "danger",
        "bg-surface-high text-muted-foreground": variant === "muted",
      })}
    >
      {label}
    </span>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function NavItem({
  href,
  label,
  icon: Icon,
  onClick,
}: {
  href: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href;

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-wide transition",
        active
          ? "bg-surface-lowest text-primary shadow-ambient"
          : "text-muted-foreground hover:bg-surface-high hover:text-foreground",
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </Link>
  );
}

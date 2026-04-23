import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { SurfaceCard, SurfaceCardContent } from "./SurfaceCard";

type StatCardProps = {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  action?: ReactNode;
  className?: string;
};

export function StatCard({ label, value, note, action, className }: StatCardProps) {
  return (
    <SurfaceCard className={cn("stat-card", className)}>
      <SurfaceCardContent className="flex h-full flex-col gap-2 pt-5">
        <span className="stat-label">{label}</span>
        <strong className="text-[1.5rem] leading-none">{value}</strong>
        {note ? <div className="text-sm text-muted-foreground">{note}</div> : null}
        {action ? <div>{action}</div> : null}
      </SurfaceCardContent>
    </SurfaceCard>
  );
}

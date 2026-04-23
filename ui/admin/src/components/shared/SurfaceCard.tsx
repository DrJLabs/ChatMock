import * as React from "react";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

function SurfaceCard({ className, ...props }: React.ComponentProps<typeof Card>) {
  return <Card className={cn("panel-card gap-0", className)} {...props} />;
}

function SurfaceCardHeader({ className, ...props }: React.ComponentProps<typeof CardHeader>) {
  return <CardHeader className={cn("px-5 pt-5 pb-4", className)} {...props} />;
}

function SurfaceCardTitle({ className, ...props }: React.ComponentProps<typeof CardTitle>) {
  return <CardTitle className={cn("text-base", className)} {...props} />;
}

function SurfaceCardDescription({
  className,
  ...props
}: React.ComponentProps<typeof CardDescription>) {
  return <CardDescription className={cn("text-sm text-muted-foreground", className)} {...props} />;
}

function SurfaceCardAction({ className, ...props }: React.ComponentProps<typeof CardAction>) {
  return <CardAction className={cn(className)} {...props} />;
}

function SurfaceCardContent({ className, ...props }: React.ComponentProps<typeof CardContent>) {
  return <CardContent className={cn("px-5 pb-5", className)} {...props} />;
}

export {
  SurfaceCard,
  SurfaceCardAction,
  SurfaceCardContent,
  SurfaceCardDescription,
  SurfaceCardHeader,
  SurfaceCardTitle,
};

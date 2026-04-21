import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        "ghost-border flex h-11 w-full rounded-xl bg-surface-low px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:bg-surface-lowest focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20",
        className,
      )}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };

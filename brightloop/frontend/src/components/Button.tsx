"use client";
import { motion } from "motion/react";
import { Loader2 } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const styles: Record<Variant, string> = {
  primary: "bg-accent text-surface hover:bg-accent/90 border border-accent",
  secondary: "bg-surface text-ink border border-line hover:border-ink",
  ghost: "text-ink hover:bg-ink/5 border border-transparent",
  danger: "bg-surface text-danger border border-danger/40 hover:bg-danger hover:text-surface",
};

type Props = Omit<ComponentProps<typeof motion.button>, "children"> & {
  variant?: Variant;
  loading?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
};

export function Button({ variant = "primary", loading, icon, children, className, disabled, ...rest }: Props) {
  const off = disabled || loading;
  return (
    <motion.button
      whileTap={off ? undefined : { scale: 0.97 }}
      whileHover={off ? undefined : { y: -1 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      disabled={off}
      className={cn(
        "inline-flex h-10 items-center justify-center gap-2 rounded px-4 text-sm font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : icon}
      {children}
    </motion.button>
  );
}

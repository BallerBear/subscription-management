"use client";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { AnimatePresence, motion } from "motion/react";
import { cn } from "@/lib/cn";

const control =
  "h-10 w-full rounded border bg-surface px-3 text-sm transition-[border-color,box-shadow] duration-200 " +
  "placeholder:text-muted/60 hover:border-ink/50 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20";

type FieldProps = { label: string; error?: string; hint?: string; children: (id: string, invalid: boolean) => ReactNode };

/** Label + control + animated error line. Forms always have real labels. */
export function Field({ label, error, hint, children }: FieldProps) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium">{label}</label>
      {children(id, !!error)}
      <AnimatePresence initial={false} mode="wait">
        {error ? (
          <motion.p
            key="err"
            role="alert"
            initial={{ opacity: 0, y: -4, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="text-xs text-danger"
          >
            {error}
          </motion.p>
        ) : hint ? (
          <p key="hint" className="text-xs text-muted">{hint}</p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string };

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, className, ...rest },
  ref,
) {
  return (
    <Field label={label} error={error} hint={hint}>
      {(id, invalid) => (
        <input
          id={id}
          ref={ref}
          aria-invalid={invalid}
          className={cn(control, invalid ? "border-danger" : "border-line", className)}
          {...rest}
        />
      )}
    </Field>
  );
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string };

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, className, children, ...rest },
  ref,
) {
  return (
    <Field label={label} error={error}>
      {(id, invalid) => (
        <select id={id} ref={ref} className={cn(control, invalid ? "border-danger" : "border-line", className)} {...rest}>
          {children}
        </select>
      )}
    </Field>
  );
});

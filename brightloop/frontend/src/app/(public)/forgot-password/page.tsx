"use client";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail } from "lucide-react";
import { AuthFrame } from "@/components/AuthFrame";
import { Button } from "@/components/Button";
import { Input } from "@/components/Field";
import { ApiError, apiRequest } from "@/lib/api";
import { forgotPasswordSchema, type ForgotPasswordValues } from "@/lib/validators";

export default function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState("");
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: "onBlur",
  });

  async function onSubmit(values: ForgotPasswordValues) {
    setFormError("");
    try {
      await apiRequest("/auth/forgot-password", { method: "POST", body: JSON.stringify(values) });
      setSentTo(values.email);
    } catch (error) {
      if (error instanceof ApiError && error.fields?.email) setError("email", { message: error.fields.email });
      else setFormError(error instanceof Error ? error.message : "Could not send the link. Try again.");
    }
  }

  if (sentTo) {
    return (
      <AuthFrame title="Check your inbox" subtitle="If that email exists, we have sent a link.">
        <p className="text-sm text-muted">
          We sent it to <span className="font-medium text-ink">{sentTo}</span>. The link works once and expires in 30 minutes.
        </p>
        <Link href="/login" className="link-u mt-8 inline-block text-sm text-accent">Back to sign in</Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title="Forgot your password?" subtitle="Enter your email and we will send you a link to choose a new one.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <Input label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}
        <Button type="submit" loading={isSubmitting} className="w-full" icon={<Mail className="h-4 w-4" />}>Send reset link</Button>
        <Link href="/login" className="link-u block text-sm text-muted">Back to sign in</Link>
      </form>
    </AuthFrame>
  );
}

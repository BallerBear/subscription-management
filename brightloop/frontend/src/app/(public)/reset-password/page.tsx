"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { AuthFrame } from "@/components/AuthFrame";
import { Button } from "@/components/Button";
import { Input } from "@/components/Field";
import { ApiError, apiRequest } from "@/lib/api";
import { resetPasswordSchema, type ResetPasswordValues } from "@/lib/validators";

function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [formError, setFormError] = useState("");
  const [done, setDone] = useState(false);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    mode: "onBlur",
  });

  async function onSubmit(values: ResetPasswordValues) {
    setFormError("");
    try {
      await apiRequest("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, password: values.password }) });
      setDone(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (error) {
      if (error instanceof ApiError && error.fields?.password) setError("password", { message: error.fields.password });
      else setFormError(error instanceof Error ? error.message : "Could not reset the password. Try again.");
    }
  }

  if (!token) {
    return (
      <AuthFrame title="Link not valid" subtitle="This reset link is missing its token.">
        <Link href="/forgot-password" className="link-u text-sm text-accent">Request a new link</Link>
      </AuthFrame>
    );
  }

  if (done) {
    return (
      <AuthFrame title="Password updated" subtitle="You can sign in with your new password.">
        <Link href="/login" className="link-u text-sm text-accent">Go to sign in</Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title="Choose a new password" subtitle="Use more than 8 characters with upper and lower case letters and a special character.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <Input label="New password" type="password" autoComplete="new-password" error={errors.password?.message} {...register("password")} />
        <Input label="Confirm new password" type="password" autoComplete="new-password" error={errors.confirm?.message} {...register("confirm")} />
        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}{" "}
            <Link href="/forgot-password" className="link-u">Request a new link</Link>
          </p>
        )}
        <Button type="submit" loading={isSubmitting} className="w-full" icon={<KeyRound className="h-4 w-4" />}>Update password</Button>
      </form>
    </AuthFrame>
  );
}

// useSearchParams needs a Suspense boundary in the Next.js App Router.
export default function ResetPasswordPage() {
  return <Suspense fallback={null}><ResetForm /></Suspense>;
}

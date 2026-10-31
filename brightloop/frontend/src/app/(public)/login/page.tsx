"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";
import { AuthFrame } from "@/components/AuthFrame";
import { Button } from "@/components/Button";
import { Input } from "@/components/Field";
import { ApiError, apiRequest } from "@/lib/api";
import { PREVIEW, homeFor, type Role, type SessionUser } from "@/lib/preview";
import { loginSchema, type LoginValues } from "@/lib/validators";

export default function LoginPage() {
  const router = useRouter();
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    mode: "onBlur", // validate when leaving a field, and on submit
  });

  async function onSubmit(values: LoginValues) {
    setFormError("");
    try {
      await apiRequest("/auth/login", { method: "POST", body: JSON.stringify(values) });
      const me = await apiRequest<SessionUser>("/auth/me");
      router.push(homeFor(me.role)); // the role decides which shell you land in
    } catch (e) {
      if (e instanceof ApiError && e.fields) Object.entries(e.fields).forEach(([k, m]) => setError(k as keyof LoginValues, { message: m }));
      else setFormError(e instanceof Error ? e.message : "Could not sign in. Try again.");
    }
  }

  function previewAs(role: Role) {
    sessionStorage.setItem("preview_role", role);
    router.push(homeFor(role));
  }

  return (
    <AuthFrame title="Welcome back" subtitle="Sign in to your Brightloop workspace.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <Input label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <Input label="Password" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}
        <Button type="submit" loading={isSubmitting} className="w-full" icon={<ArrowRight className="h-4 w-4" />}>Sign in</Button>
        <div className="flex justify-between text-sm">
          <Link href="/signup" className="link-u text-accent">Create an account</Link>
          <Link href="/forgot-password" className="link-u text-muted">Forgot password?</Link>
        </div>
      </form>

      {PREVIEW && (
        <div className="mt-10 border-t border-line pt-6">
          <p className="mb-3 text-xs uppercase tracking-[0.14em] text-muted">UI preview, no login needed</p>
          <div className="grid grid-cols-3 gap-2">
            {(["ADMIN", "STAFF", "CUSTOMER"] as Role[]).map((r) => (
              <Button key={r} type="button" variant="secondary" className="h-9 px-2 text-xs capitalize" onClick={() => previewAs(r)}>{r.toLowerCase()}</Button>
            ))}
          </div>
        </div>
      )}
    </AuthFrame>
  );
}

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthFrame } from "@/components/AuthFrame";
import { Button } from "@/components/Button";
import { Input } from "@/components/Field";
import { ApiError, apiRequest } from "@/lib/api";
import { signupSchema, type SignupValues } from "@/lib/validators";

export default function SignupPage() {
  const router = useRouter();
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    mode: "onBlur",
  });

  async function onSubmit(values: SignupValues) {
    setFormError("");
    try {
      await apiRequest("/auth/signup", { method: "POST", body: JSON.stringify(values) });
      router.push("/portal"); // signup always creates a CUSTOMER
    } catch (e) {
      if (e instanceof ApiError && e.fields) Object.entries(e.fields).forEach(([k, m]) => setError(k as keyof SignupValues, { message: m }));
      else setFormError(e instanceof Error ? e.message : "Could not create the account. Try again.");
    }
  }

  return (
    <AuthFrame title="Create your account" subtitle="See your subscriptions and invoices in one place.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <Input label="Full name" autoComplete="name" error={errors.name?.message} {...register("name")} />
        <Input label="Company name" autoComplete="organization" error={errors.company_name?.message} {...register("company_name")} />
        <Input label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <Input label="Password" type="password" autoComplete="new-password" hint="9+ characters with upper, lower and a special character." error={errors.password?.message} {...register("password")} />
        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}
        <Button type="submit" loading={isSubmitting} className="w-full">Create account</Button>
        <p className="text-sm text-muted">Already registered? <Link href="/login" className="link-u text-accent">Sign in</Link></p>
      </form>
    </AuthFrame>
  );
}

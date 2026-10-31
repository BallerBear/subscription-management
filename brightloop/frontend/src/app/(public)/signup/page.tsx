"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthFrame } from "@/components/AuthFrame";
import { Button } from "@/components/Button";
import { Input } from "@/components/Field";
import { ApiError, apiRequest, setAccessToken } from "@/lib/api";
import { homeFor, type SessionUser } from "@/lib/preview";
import { signupSchema, type SignupValues } from "@/lib/validators";

type AuthResponse = { user: SessionUser; access_token: string; token_type: "bearer" };

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
      const result = await apiRequest<AuthResponse>("/auth/register", {
        method: "POST",
        // The registration API requires a customer contact name as well as the account name.
        body: JSON.stringify({ ...values, contact_name: values.name }),
      });
      setAccessToken(result.access_token);
      router.push(homeFor(result.user.role));
    } catch (error) {
      if (error instanceof ApiError && error.fields) {
        Object.entries(error.fields).forEach(([field, message]) => {
          setError(field as keyof SignupValues, { message });
        });
      } else {
        setFormError(error instanceof Error ? error.message : "Could not create the account. Try again.");
      }
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

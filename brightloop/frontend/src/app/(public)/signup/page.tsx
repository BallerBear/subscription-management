"use client";

import Link from "next/link";
import { useState } from "react";
import Field from "@/components/Field";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import { signupSchema, validate, type Errors } from "@/lib/validators";

export default function SignupPage() {
  const [form, setForm] = useState({ name: "", email: "", company_name: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (key: keyof typeof form) => (v: string) => setForm({ ...form, [key]: v });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    const result = validate(signupSchema, form);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      await api<CurrentUser>("/auth/signup", { body: result.data });
      window.location.assign("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields);
        setFormError(err.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
      setLoading(false);
    }
  }

  return (
    <section className="auth">
      <aside className="auth-aside">
        <h2>Set up your company account.</h2>
        <p>Your company details are used on every invoice, so enter them the way you want them printed.</p>
      </aside>
      <form className="auth-form" onSubmit={submit} noValidate>
        <h1>Create account</h1>
        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        <Field label="Full name" name="name" autoComplete="name" value={form.name}
          onChange={set("name")} error={errors.name} />
        <Field label="Company name" name="company_name" autoComplete="organization" value={form.company_name}
          onChange={set("company_name")} error={errors.company_name} />
        <Field label="Email" name="email" type="email" autoComplete="email" value={form.email}
          onChange={set("email")} error={errors.email} />
        <Field label="Password" name="password" type="password" autoComplete="new-password" value={form.password}
          onChange={set("password")} error={errors.password} hint="At least 8 characters" />
        <button className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </button>
        <p className="auth-switch">
          Already have an account? <Link href="/login">Log in</Link>
        </p>
      </form>
    </section>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Field from "@/components/Field";
import { api, ApiError, type CurrentUser } from "@/lib/api";
import { loginSchema, validate, type Errors } from "@/lib/validators";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    const result = validate(loginSchema, form);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      await api<CurrentUser>("/auth/login", { body: result.data });
      window.location.assign("/"); // full reload so the header picks up the new session
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
        <h2>Subscriptions that bill themselves.</h2>
        <p>See your plans, invoices and payments for your Brightloop account in one place.</p>
      </aside>
      <form className="auth-form" onSubmit={submit} noValidate>
        <h1>Log in</h1>
        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        <Field label="Email" name="email" type="email" autoComplete="email" value={form.email}
          onChange={(v) => setForm({ ...form, email: v })} error={errors.email} />
        <Field label="Password" name="password" type="password" autoComplete="current-password" value={form.password}
          onChange={(v) => setForm({ ...form, password: v })} error={errors.password} />
        <button className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Logging in…" : "Log in"}
        </button>
        <p className="auth-switch">
          New to Brightloop? <Link href="/signup">Create an account</Link>
        </p>
      </form>
    </section>
  );
}

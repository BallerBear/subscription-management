"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { UserPlus } from "lucide-react";
import { Button } from "../Button";
import { Input } from "../Field";
import { PageHeader, Panel, PanelHeader } from "../Panel";
import { Reveal } from "../motion";
import { StatusDot } from "../StatusDot";
import { DataList } from "./DataList";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/money";
import { useUser } from "@/lib/session";
import { staffSchema, type StaffValues } from "@/lib/validators";

type Member = { id: number; name: string; email: string; role: string; is_active: boolean; created_at: string };

function StaffForm({ onDone }: { onDone: () => void }) {
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<StaffValues>({
    resolver: zodResolver(staffSchema), mode: "onBlur", defaultValues: { name: "", email: "", password: "" },
  });
  async function onSubmit(values: StaffValues) {
    setFormError("");
    try {
      await apiRequest("/auth/staff", { method: "POST", body: JSON.stringify(values) });
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.fields && Object.keys(e.fields).length) {
        Object.entries(e.fields).forEach(([f, message]) => setError(f as keyof StaffValues, { message }));
      } else setFormError(e instanceof Error ? e.message : "Could not create the account.");
    }
  }
  return (
    <Panel className="mb-6">
      <PanelHeader title="New staff account" />
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="grid gap-5 p-5 md:grid-cols-3">
        <Input label="Full name" error={errors.name?.message} {...register("name")} />
        <Input label="Email" type="email" autoComplete="off" error={errors.email?.message} {...register("email")} />
        <Input label="Temporary password" type="password" autoComplete="new-password"
          hint="9+ characters with upper, lower and a special character" error={errors.password?.message} {...register("password")} />
        <div className="flex items-center justify-end gap-3 md:col-span-3">
          {formError && <p role="alert" className="mr-auto text-sm text-danger">{formError}</p>}
          <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button>
          <Button type="submit" loading={isSubmitting}>Create staff account</Button>
        </div>
      </form>
    </Panel>
  );
}

export function TeamPage() {
  const me = useUser();
  const [adding, setAdding] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState("");

  async function toggle(m: Member) {
    setError("");
    try {
      await apiRequest(`/users/${m.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !m.is_active }) });
      setRefresh((n) => n + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update the account."); }
  }

  return (
    <Reveal>
      <PageHeader eyebrow="Admin only" title="Staff accounts" subtitle="People who can run billing and record payments."
        action={!adding && <Button icon={<UserPlus className="h-4 w-4" />} onClick={() => setAdding(true)}>Add staff</Button>} />
      {adding && <StaffForm onDone={() => { setAdding(false); setRefresh((n) => n + 1); }} />}
      {error && <p role="alert" className="mb-3 text-sm text-danger">{error}</p>}
      <DataList<Member>
        path="/users" refreshKey={refresh} emptyTitle="No staff yet" emptyBody="Add a staff account to share the billing work."
        columns={[
          { header: "Name", cell: (r) => <span className="font-medium">{r.name}</span> },
          { header: "Email", cell: (r) => r.email },
          { header: "Role", cell: (r) => <span className="capitalize">{r.role.toLowerCase()}</span> },
          { header: "Since", numeric: true, cell: (r) => formatDate(r.created_at.slice(0, 10)) },
          { header: "Status", cell: (r) => <StatusDot status={r.is_active ? "ACTIVE" : "CLOSED"} /> },
          { header: "", numeric: true, cell: (r) => r.role === "STAFF" && r.id !== me.id
              ? <Button variant={r.is_active ? "danger" : "secondary"} className="h-8 px-3" onClick={() => toggle(r)}>{r.is_active ? "Deactivate" : "Reactivate"}</Button> : null },
        ]}
      />
    </Reveal>
  );
}

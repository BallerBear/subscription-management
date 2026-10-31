"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { Button } from "../Button";
import { Input } from "../Field";
import { PageHeader, Panel, PanelHeader } from "../Panel";
import { Reveal } from "../motion";
import { StatusDot } from "../StatusDot";
import { DataList } from "./DataList";
import { ApiError, apiRequest } from "@/lib/api";
import { customerSchema, type CustomerValues } from "@/lib/validators";

type Customer = {
  id: number; company_name: string; contact_name: string; email: string; phone: string | null;
  city: string | null; state: string | null; gstin: string | null; is_active: boolean; active_subscriptions: number;
};

function CustomerForm({ onDone }: { onDone: () => void }) {
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<CustomerValues>({
    resolver: zodResolver(customerSchema), mode: "onBlur",
    defaultValues: { company_name: "", contact_name: "", email: "", phone: "", city: "", state: "", gstin: "" },
  });

  async function onSubmit(values: CustomerValues) {
    setFormError("");
    try {
      await apiRequest("/customers", { method: "POST", body: JSON.stringify(values) });
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.fields && Object.keys(e.fields).length) {
        Object.entries(e.fields).forEach(([f, message]) => setError(f as keyof CustomerValues, { message }));
      } else setFormError(e instanceof Error ? e.message : "Could not save the customer.");
    }
  }

  return (
    <Panel className="mb-6">
      <PanelHeader title="New customer" />
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="grid gap-5 p-5 md:grid-cols-2">
        <Input label="Company name" error={errors.company_name?.message} {...register("company_name")} />
        <Input label="Contact person" error={errors.contact_name?.message} {...register("contact_name")} />
        <Input label="Email" type="email" error={errors.email?.message} {...register("email")} />
        <Input label="Phone" hint="Optional" error={errors.phone?.message} {...register("phone")} />
        <Input label="City" error={errors.city?.message} {...register("city")} />
        <Input label="State" error={errors.state?.message} {...register("state")} />
        <Input label="GSTIN" hint="Optional, e.g. 33AABCK1234F1Z5" error={errors.gstin?.message} {...register("gstin")} />
        <div className="flex items-end justify-end gap-3">
          {formError && <p role="alert" className="mr-auto text-sm text-danger">{formError}</p>}
          <Button type="button" variant="ghost" onClick={onDone}>Cancel</Button>
          <Button type="submit" loading={isSubmitting}>Save customer</Button>
        </div>
      </form>
    </Panel>
  );
}

export function CustomersPage() {
  const [adding, setAdding] = useState(false);
  const [refresh, setRefresh] = useState(0);
  return (
    <Reveal>
      <PageHeader eyebrow="People" title="Customers" subtitle="Everyone Brightloop bills."
        action={!adding && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setAdding(true)}>Add customer</Button>} />
      {adding && <CustomerForm onDone={() => { setAdding(false); setRefresh((n) => n + 1); }} />}
      <DataList<Customer>
        path="/customers" refreshKey={refresh} searchLabel="Search name or email"
        emptyTitle="No customers found" emptyBody="Add your first customer to start building subscriptions."
        columns={[
          { header: "Company", cell: (r) => <span className="font-medium">{r.company_name}</span> },
          { header: "Contact", cell: (r) => <div>{r.contact_name}<p className="text-xs text-muted">{r.email}</p></div> },
          { header: "Location", cell: (r) => [r.city, r.state].filter(Boolean).join(", ") || <span className="text-muted">-</span> },
          { header: "GSTIN", cell: (r) => <span className="num text-xs">{r.gstin ?? "-"}</span> },
          { header: "Active subs", numeric: true, cell: (r) => r.active_subscriptions },
          { header: "Status", cell: (r) => <StatusDot status={r.is_active ? "ACTIVE" : "CLOSED"} /> },
        ]}
      />
    </Reveal>
  );
}

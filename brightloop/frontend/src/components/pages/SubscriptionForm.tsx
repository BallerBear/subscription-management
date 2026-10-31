"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useFieldArray, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "../Button";
import { Input, Select } from "../Field";
import { PageHeader, Panel, PanelHeader } from "../Panel";
import { Reveal } from "../motion";
import { ErrorState, Skeleton } from "../States";
import { ApiError, apiRequest } from "@/lib/api";
import { formatMoney } from "@/lib/money";
import { useBase } from "@/lib/useBase";
import { useQuery } from "@/lib/useQuery";
import { subscriptionSchema, type SubscriptionValues } from "@/lib/validators";

type Lookups = {
  plans: { id: number; name: string; price: number; billing_period: string; min_quantity: number }[];
  products: { id: number; name: string; sales_price: number; variants: { id: number; label: string; extra_price: number }[] }[];
  payment_terms: { id: number; name: string; days: number }[];
};

const plusYear = (iso: string) => `${Number(iso.slice(0, 4)) + 1}${iso.slice(4)}`;

export function SubscriptionForm() {
  const router = useRouter();
  const base = useBase();
  const lookups = useQuery<Lookups>("/lookups");
  const customers = useQuery<{ items: { id: number; company_name: string }[] }>("/customers?page_size=100");
  const clock = useQuery<{ today: string }>("/clock");
  const [formError, setFormError] = useState("");

  const form = useForm<SubscriptionValues>({
    resolver: zodResolver(subscriptionSchema) as Resolver<SubscriptionValues>,
    mode: "onBlur",
    values: clock.data ? {
      customer_id: 0, plan_id: 0, payment_term_id: 0,
      start_date: clock.data.today, expiry_date: plusYear(clock.data.today),
      lines: [{ product_id: 0, variant_id: 0, quantity: 1 }],
    } : undefined,
  });
  const { register, handleSubmit, control, watch, setError, formState: { errors, isSubmitting } } = form;
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });

  if (lookups.error || customers.error) return <ErrorState message={lookups.error ?? customers.error ?? ""} onRetry={() => { lookups.refetch(); customers.refetch(); }} />;
  if (!lookups.data || !customers.data || !clock.data) return <Skeleton className="h-96 w-full" />;
  const { plans, products, payment_terms } = lookups.data;
  const plan = plans.find((p) => p.id === Number(watch("plan_id")));

  async function onSubmit(v: SubscriptionValues) {
    setFormError("");
    // the database does not check this rule, so the app does (browser here, server again on save)
    const bad = plan ? v.lines.findIndex((l) => l.quantity < plan.min_quantity) : -1;
    if (plan && bad >= 0) {
      setError(`lines.${bad}.quantity`, { message: `${plan.name} needs at least ${plan.min_quantity} per product` });
      return;
    }
    try {
      const created = await apiRequest<{ id: number }>("/subscriptions", {
        method: "POST",
        body: JSON.stringify({ ...v, lines: v.lines.map((l) => ({ ...l, variant_id: l.variant_id || null })) }),
      });
      router.push(`${base}/subscriptions/${created.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.fields && Object.keys(e.fields).length) {
        Object.entries(e.fields).forEach(([f, message]) => setError(f as keyof SubscriptionValues, { message }));
      }
      setFormError(e instanceof Error ? e.message : "Could not create the subscription.");
    }
  }

  return (
    <Reveal>
      <PageHeader eyebrow="Subscriptions" title="New subscription" subtitle="Prices and tax are copied onto the subscription now, so later catalog changes never rewrite it." />
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        <Panel>
          <PanelHeader title="Customer and plan" />
          <div className="grid gap-5 p-5 md:grid-cols-2">
            <Select label="Customer" error={errors.customer_id?.message} {...register("customer_id")}>
              <option value={0}>Choose a customer</option>
              {customers.data.items.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
            </Select>
            <Select label="Plan" error={errors.plan_id?.message} {...register("plan_id")}>
              <option value={0}>Choose a plan</option>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.billing_period.toLowerCase()})</option>)}
            </Select>
            <Select label="Payment terms" error={errors.payment_term_id?.message} {...register("payment_term_id")}>
              <option value={0}>Choose terms</option>
              {payment_terms.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </Select>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Start date" type="date" error={errors.start_date?.message} {...register("start_date")} />
              <Input label="Expiry date" type="date" error={errors.expiry_date?.message} {...register("expiry_date")} />
            </div>
          </div>
          {plan && <p className="border-t border-line px-5 py-3 text-sm text-muted">
            {plan.name}: {plan.price > 0 ? <>a plan fee of <span className="num text-ink">{formatMoney(plan.price)}</span> is added each period, and </> : ""}
            every product needs a quantity of at least <span className="num text-ink">{plan.min_quantity}</span>.
          </p>}
        </Panel>

        <Panel>
          <PanelHeader title="Products" action={
            <Button type="button" variant="secondary" className="h-8 px-3" icon={<Plus className="h-4 w-4" />}
              onClick={() => append({ product_id: 0, variant_id: 0, quantity: plan?.min_quantity ?? 1 })}>Add product</Button>} />
          <div className="divide-y divide-line">
            {fields.map((f, i) => {
              const product = products.find((p) => p.id === Number(watch(`lines.${i}.product_id`)));
              return (
                <div key={f.id} className="grid items-start gap-4 p-5 md:grid-cols-[2fr_1.5fr_110px_auto]">
                  <Select label="Product" error={errors.lines?.[i]?.product_id?.message} {...register(`lines.${i}.product_id`)}>
                    <option value={0}>Choose a product</option>
                    {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({formatMoney(p.sales_price)})</option>)}
                  </Select>
                  <Select label="Variant" disabled={!product?.variants.length} {...register(`lines.${i}.variant_id`)}>
                    <option value={0}>{product?.variants.length ? "No variant" : "None available"}</option>
                    {product?.variants.map((v) => <option key={v.id} value={v.id}>{v.label} (+{formatMoney(v.extra_price)})</option>)}
                  </Select>
                  <Input label="Quantity" type="number" min={1} error={errors.lines?.[i]?.quantity?.message} {...register(`lines.${i}.quantity`)} />
                  <Button type="button" variant="ghost" className="mt-6 px-2" aria-label="Remove product" disabled={fields.length === 1} onClick={() => remove(i)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              );
            })}
          </div>
          {errors.lines?.message && <p role="alert" className="px-5 pb-4 text-xs text-danger">{errors.lines.message}</p>}
        </Panel>

        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>
          <Button type="submit" loading={isSubmitting}>Create subscription</Button>
        </div>
      </form>
    </Reveal>
  );
}

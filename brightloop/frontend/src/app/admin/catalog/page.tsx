"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Layers, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/Button";
import { Input, Select } from "@/components/Field";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/States";
import { PageHeader, Panel, PanelHeader } from "@/components/Panel";
import { Table, type Column } from "@/components/Table";
import { ApiError, apiRequest } from "@/lib/api";
import { formatMoney } from "@/lib/money";

type Tab = "products" | "plans" | "taxes";
type PageResult<T> = { items: T[]; total: number; page: number; page_size: number };
type Tax = { id: number; name: string; rate_bps: number; is_active: boolean };
type Product = {
  id: number; name: string; type: string; sales_price: number; cost_price: number;
  tax_id: number; tax_name?: string; is_active: boolean;
};
type Plan = {
  id: number; name: string; price: number; billing_period: string; min_quantity: number;
  available_from: string; available_to: string | null; tax_id: number | null;
  tax_name?: string | null; auto_close: boolean; allow_early_close: boolean;
  allow_pause: boolean; allow_renew: boolean; is_active: boolean;
};
type EditTarget = { kind: Tab; id: number };
type Variant = { id: number; product_id: number; attribute: string; value: string; extra_price: number; is_active: boolean };

const toPaise = (rupees: string) => Math.round(Number(rupees) * 100);
const activeLabel = (active: boolean) => active ? "Active" : "Inactive";

export default function CatalogPage() {
  const [tab, setTab] = useState<Tab>("products");
  const [taxes, setTaxes] = useState<Tax[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [expandedProduct, setExpandedProduct] = useState<number | null>(null);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [variantLoading, setVariantLoading] = useState(false);
  const [variantAttribute, setVariantAttribute] = useState("");
  const [variantValue, setVariantValue] = useState("");
  const [variantPrice, setVariantPrice] = useState("0");
  const [editingVariantId, setEditingVariantId] = useState<number | null>(null);

  const [taxName, setTaxName] = useState("");
  const [taxRate, setTaxRate] = useState("18");
  const [productName, setProductName] = useState("");
  const [productType, setProductType] = useState("SOFTWARE");
  const [productPrice, setProductPrice] = useState("");
  const [productCost, setProductCost] = useState("0");
  const [productTax, setProductTax] = useState("");
  const [planName, setPlanName] = useState("");
  const [planPrice, setPlanPrice] = useState("0");
  const [planPeriod, setPlanPeriod] = useState("MONTHLY");
  const [planMinQuantity, setPlanMinQuantity] = useState("1");
  const [planFrom, setPlanFrom] = useState(new Date().toISOString().slice(0, 10));
  const [planTo, setPlanTo] = useState("");
  const [planTax, setPlanTax] = useState("");
  const [autoClose, setAutoClose] = useState(false);
  const [allowEarlyClose, setAllowEarlyClose] = useState(true);
  const [allowPause, setAllowPause] = useState(false);
  const [allowRenew, setAllowRenew] = useState(true);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [taxResult, productResult, planResult] = await Promise.all([
        apiRequest<PageResult<Tax>>("/catalog/taxes?page=1&page_size=100"),
        apiRequest<PageResult<Product>>("/catalog/products?page=1&page_size=100"),
        apiRequest<PageResult<Plan>>("/catalog/plans?page=1&page_size=100"),
      ]);
      setTaxes(taxResult.items);
      setProducts(productResult.items);
      setPlans(planResult.items);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : "Could not load the catalogue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);

  function startEditTax(tax: Tax) {
    setTab("taxes");
    setTaxName(tax.name);
    setTaxRate((tax.rate_bps / 100).toString());
    setEditTarget({ kind: "taxes", id: tax.id });
    setShowForm(true);
    setError("");
    setNotice("");
  }

  function startEditProduct(product: Product) {
    setTab("products");
    setProductName(product.name);
    setProductType(product.type);
    setProductPrice((product.sales_price / 100).toFixed(2));
    setProductCost((product.cost_price / 100).toFixed(2));
    setProductTax(String(product.tax_id));
    setEditTarget({ kind: "products", id: product.id });
    setShowForm(true);
    setError("");
    setNotice("");
  }

  function startEditPlan(plan: Plan) {
    setTab("plans");
    setPlanName(plan.name);
    setPlanPrice((plan.price / 100).toFixed(2));
    setPlanPeriod(plan.billing_period);
    setPlanMinQuantity(String(plan.min_quantity));
    setPlanFrom(plan.available_from.slice(0, 10));
    setPlanTo(plan.available_to?.slice(0, 10) ?? "");
    setPlanTax(plan.tax_id === null ? "" : String(plan.tax_id));
    setAutoClose(plan.auto_close);
    setAllowEarlyClose(plan.allow_early_close);
    setAllowPause(plan.allow_pause);
    setAllowRenew(plan.allow_renew);
    setEditTarget({ kind: "plans", id: plan.id });
    setShowForm(true);
    setError("");
    setNotice("");
  }

  async function createItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      if (tab === "taxes") {
        await apiRequest(editTarget ? `/catalog/taxes/${editTarget.id}` : "/catalog/taxes", {
          method: editTarget ? "PATCH" : "POST",
          body: JSON.stringify({ name: taxName, rate_bps: Math.round(Number(taxRate) * 100) }),
        });
        setTaxName("");
        setTaxRate("18");
        setNotice(editTarget ? "Tax rule updated." : "Tax rule created.");
      } else if (tab === "products") {
        await apiRequest(editTarget ? `/catalog/products/${editTarget.id}` : "/catalog/products", {
          method: editTarget ? "PATCH" : "POST",
          body: JSON.stringify({
            name: productName,
            type: productType,
            sales_price: toPaise(productPrice),
            cost_price: toPaise(productCost || "0"),
            tax_id: Number(productTax),
          }),
        });
        setProductName("");
        setProductPrice("");
        setProductCost("0");
        setProductTax("");
        setNotice(editTarget ? "Product updated." : "Product created.");
      } else {
        if (Number(planPrice || "0") > 0 && !planTax) {
          throw new Error("Choose a tax rule for a plan with a fee.");
        }
        await apiRequest(editTarget ? `/catalog/plans/${editTarget.id}` : "/catalog/plans", {
          method: editTarget ? "PATCH" : "POST",
          body: JSON.stringify({
            name: planName,
            price: toPaise(planPrice || "0"),
            billing_period: planPeriod,
            min_quantity: Number(planMinQuantity),
            available_from: planFrom,
            available_to: planTo || null,
            tax_id: planTax ? Number(planTax) : null,
            auto_close: autoClose,
            allow_early_close: allowEarlyClose,
            allow_pause: allowPause,
            allow_renew: allowRenew,
          }),
        });
        setPlanName("");
        setPlanPrice("0");
        setPlanTax("");
        setPlanTo("");
        setNotice(editTarget ? "Subscription plan updated." : "Subscription plan created.");
      }
      setShowForm(false);
      setEditTarget(null);
      await loadCatalog();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : "Could not save this catalogue item.");
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(kind: "taxes" | "products" | "plans", id: number) {
    if (!window.confirm("Deactivate this item? Existing subscriptions and invoices will retain their references.")) return;
    setError("");
    setNotice("");
    try {
      await apiRequest(`/catalog/${kind}/${id}`, { method: "DELETE" });
      setNotice("Item deactivated.");
      await loadCatalog();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : cause instanceof Error ? cause.message : "Could not deactivate this item.");
    }
  }

  async function toggleVariants(productId: number) {
    if (expandedProduct === productId) {
      setExpandedProduct(null);
      return;
    }
    setExpandedProduct(productId);
    setEditingVariantId(null);
    setVariantAttribute("");
    setVariantValue("");
    setVariantPrice("0");
    setVariantLoading(true);
    setError("");
    try {
      const result = await apiRequest<Variant[]>(`/catalog/products/${productId}/variants`);
      setVariants(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load product variants.");
    } finally {
      setVariantLoading(false);
    }
  }

  async function addVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (expandedProduct === null) return;
    setSaving(true);
    setError("");
    try {
      await apiRequest(
        editingVariantId === null
          ? `/catalog/products/${expandedProduct}/variants`
          : `/catalog/products/${expandedProduct}/variants/${editingVariantId}`,
        {
          method: editingVariantId === null ? "POST" : "PATCH",
        body: JSON.stringify({
          attribute: variantAttribute,
          value: variantValue,
          extra_price: toPaise(variantPrice || "0"),
        }),
      });
      setVariantAttribute("");
      setVariantValue("");
      setVariantPrice("0");
      setVariants(await apiRequest<Variant[]>(`/catalog/products/${expandedProduct}/variants`));
      setNotice(editingVariantId === null ? "Variant added." : "Variant updated.");
      setEditingVariantId(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not add this variant.");
    } finally {
      setSaving(false);
    }
  }

  function startEditVariant(variant: Variant) {
    setVariantAttribute(variant.attribute);
    setVariantValue(variant.value);
    setVariantPrice((variant.extra_price / 100).toFixed(2));
    setEditingVariantId(variant.id);
    setError("");
    setNotice("");
  }

  async function deactivateVariant(variantId: number) {
    if (expandedProduct === null) return;
    try {
      await apiRequest(`/catalog/products/${expandedProduct}/variants/${variantId}`, { method: "DELETE" });
      if (editingVariantId === variantId) {
        setEditingVariantId(null);
        setVariantAttribute("");
        setVariantValue("");
        setVariantPrice("0");
      }
      setVariants(await apiRequest<Variant[]>(`/catalog/products/${expandedProduct}/variants`));
      setNotice("Variant deactivated.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not deactivate this variant.");
    }
  }

  const taxColumns: Column<Tax>[] = [
    { header: "Tax name", cell: (tax) => <span className="font-medium">{tax.name}</span> },
    { header: "Rate", numeric: true, cell: (tax) => `${(tax.rate_bps / 100).toFixed(2)}%` },
    { header: "Status", cell: (tax) => activeLabel(tax.is_active) },
    { header: "", cell: (tax) => <div className="flex items-center gap-2"><Button variant="ghost" className="h-8 px-2" onClick={() => startEditTax(tax)}><Pencil className="h-3.5 w-3.5" /> Edit</Button>{tax.is_active ? <Button variant="danger" className="h-8 px-2" onClick={() => void deactivate("taxes", tax.id)}><Trash2 className="h-3.5 w-3.5" /> Deactivate</Button> : null}</div> },
  ];
  const productColumns: Column<Product>[] = [
    { header: "Product", cell: (product) => <><span className="font-medium">{product.name}</span><span className="ml-2 text-xs text-muted">{product.type.replace("_", " ").toLowerCase()}</span></> },
    { header: "Sales price", numeric: true, cell: (product) => formatMoney(product.sales_price) },
    { header: "Tax", cell: (product) => product.tax_name ?? "—" },
    { header: "Status", cell: (product) => activeLabel(product.is_active) },
    { header: "", cell: (product) => <Button variant="ghost" className="h-8 px-2" onClick={() => startEditProduct(product)}><Pencil className="h-3.5 w-3.5" /> Edit</Button> },
    { header: "Variants", cell: (product) => <Button variant="ghost" className="h-8 px-2" onClick={() => void toggleVariants(product.id)}><Layers className="h-3.5 w-3.5" /> Manage</Button> },
    { header: "", cell: (product) => product.is_active ? <Button variant="danger" className="h-8 px-2" onClick={() => void deactivate("products", product.id)}><Trash2 className="h-3.5 w-3.5" /> Deactivate</Button> : null },
  ];
  const planColumns: Column<Plan>[] = [
    { header: "Plan", cell: (plan) => <span className="font-medium">{plan.name}</span> },
    { header: "Price", numeric: true, cell: (plan) => formatMoney(plan.price) },
    { header: "Billing", cell: (plan) => plan.billing_period.toLowerCase() },
    { header: "Minimum quantity", numeric: true, cell: (plan) => plan.min_quantity },
    { header: "Tax", cell: (plan) => plan.tax_name ?? "—" },
    { header: "Status", cell: (plan) => activeLabel(plan.is_active) },
    { header: "", cell: (plan) => <div className="flex items-center gap-2"><Button variant="ghost" className="h-8 px-2" onClick={() => startEditPlan(plan)}><Pencil className="h-3.5 w-3.5" /> Edit</Button>{plan.is_active ? <Button variant="danger" className="h-8 px-2" onClick={() => void deactivate("plans", plan.id)}><Trash2 className="h-3.5 w-3.5" /> Deactivate</Button> : null}</div> },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Admin console"
        title="Catalog"
        subtitle="Manage the products, pricing plans and tax rules used when preparing subscriptions."
        action={<Button onClick={() => { setEditTarget(null); setShowForm((visible) => !visible); }} icon={<Plus className="h-4 w-4" />}>{showForm ? "Close form" : "New item"}</Button>}
      />

      <div className="mb-6 flex flex-wrap gap-2" role="tablist" aria-label="Catalogue sections">
        {(["products", "plans", "taxes"] as Tab[]).map((item) => (
          <Button key={item} variant={tab === item ? "primary" : "secondary"} onClick={() => { setTab(item); setShowForm(false); setEditTarget(null); setNotice(""); }}>
            {item[0].toUpperCase() + item.slice(1)}
          </Button>
        ))}
        <div className="flex-1" />
        <Button variant="ghost" onClick={() => void loadCatalog()} loading={loading} icon={<RefreshCw className="h-4 w-4" />}>Refresh</Button>
      </div>

      {notice && <p role="status" className="mb-4 text-sm text-accent">{notice}</p>}
      {error && <div className="mb-4"><ErrorState message={error} onRetry={() => void loadCatalog()} /></div>}

      {showForm && (
        <Panel className="mb-6 p-5">
          <PanelHeader title={`${editTarget ? "Edit" : "Create"} ${tab === "taxes" ? "tax rule" : tab === "products" ? "product" : "subscription plan"}`} />
          <form onSubmit={(event) => void createItem(event)} className="mt-5 space-y-4">
            {tab === "taxes" && (
              <div className="grid gap-4 md:grid-cols-2">
                <Input label="Tax name" value={taxName} onChange={(event) => setTaxName(event.target.value)} required maxLength={100} />
                <Input label="Tax rate (%)" type="number" min="0" max="100" step="0.01" value={taxRate} onChange={(event) => setTaxRate(event.target.value)} required />
              </div>
            )}
            {tab === "products" && (
              <div className="grid gap-4 md:grid-cols-2">
                <Input label="Product name" value={productName} onChange={(event) => setProductName(event.target.value)} required maxLength={200} />
                <Select label="Product type" value={productType} onChange={(event) => setProductType(event.target.value)}>
                  <option value="SOFTWARE">Software</option><option value="ADD_ON">Add-on</option><option value="SERVICE">Service</option>
                </Select>
                <Input label="Sales price (₹)" type="number" min="0" step="0.01" value={productPrice} onChange={(event) => setProductPrice(event.target.value)} required />
                <Input label="Cost price (₹)" type="number" min="0" step="0.01" value={productCost} onChange={(event) => setProductCost(event.target.value)} />
                <Select label="Tax rule" value={productTax} onChange={(event) => setProductTax(event.target.value)} required>
                  <option value="">Choose a tax rule</option>
                  {taxes.filter((tax) => tax.is_active || Number(productTax) === tax.id).map((tax) => <option key={tax.id} value={tax.id}>{tax.name} ({(tax.rate_bps / 100).toFixed(2)}%){!tax.is_active ? " · inactive" : ""}</option>)}
                </Select>
              </div>
            )}
            {tab === "plans" && (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Input label="Plan name" value={planName} onChange={(event) => setPlanName(event.target.value)} required maxLength={200} />
                  <Input label="Plan fee (₹)" type="number" min="0" step="0.01" value={planPrice} onChange={(event) => setPlanPrice(event.target.value)} required />
                  <Select label="Billing period" value={planPeriod} onChange={(event) => setPlanPeriod(event.target.value)}>
                    <option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="MONTHLY">Monthly</option><option value="YEARLY">Yearly</option>
                  </Select>
                  <Input label="Minimum quantity" type="number" min="1" step="1" value={planMinQuantity} onChange={(event) => setPlanMinQuantity(event.target.value)} required />
                  <Input label="Available from" type="date" value={planFrom} onChange={(event) => setPlanFrom(event.target.value)} required />
                  <Input label="Available until (optional)" type="date" value={planTo} onChange={(event) => setPlanTo(event.target.value)} />
                  <Select label="Tax rule (required for a fee)" value={planTax} onChange={(event) => setPlanTax(event.target.value)}>
                    <option value="">No tax rule</option>
                    {taxes.filter((tax) => tax.is_active || Number(planTax) === tax.id).map((tax) => <option key={tax.id} value={tax.id}>{tax.name} ({(tax.rate_bps / 100).toFixed(2)}%){!tax.is_active ? " · inactive" : ""}</option>)}
                  </Select>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={autoClose} onChange={(event) => setAutoClose(event.target.checked)} /> Automatically close</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={allowEarlyClose} onChange={(event) => setAllowEarlyClose(event.target.checked)} /> Allow early closure</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={allowPause} onChange={(event) => setAllowPause(event.target.checked)} /> Allow pause</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={allowRenew} onChange={(event) => setAllowRenew(event.target.checked)} /> Allow renewal</label>
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => { setShowForm(false); setEditTarget(null); }}>Cancel</Button>
              <Button type="submit" loading={saving}>{editTarget ? "Save changes" : `Create ${tab === "taxes" ? "tax" : tab === "products" ? "product" : "plan"}`}</Button>
            </div>
          </form>
        </Panel>
      )}

      <Panel>
        <PanelHeader title={tab === "taxes" ? "Tax rules" : tab === "products" ? "Products" : "Subscription plans"} />
        {loading ? <TableSkeleton cols={tab === "products" ? 6 : tab === "plans" ? 7 : 4} /> : (
          <>
            {tab === "taxes" && (taxes.length ? <Table columns={taxColumns} rows={taxes} /> : <EmptyState title="No tax rules yet" body="Create a tax rule before adding taxable products or plans." />)}
            {tab === "products" && (products.length ? <Table columns={productColumns} rows={products} /> : <EmptyState title="No products yet" body="Add your first product to begin building the catalogue." />)}
            {tab === "plans" && (plans.length ? <Table columns={planColumns} rows={plans} /> : <EmptyState title="No plans yet" body="Create a billing plan to use when preparing subscriptions." />)}
          </>
        )}
      </Panel>

      {expandedProduct !== null && (
        <Panel className="mt-6">
          <PanelHeader title={`Product variants · ${products.find((product) => product.id === expandedProduct)?.name ?? ""}`} />
          {variantLoading ? <TableSkeleton rows={3} cols={4} /> : (
            <div className="p-5">
              {variants.length ? (
                <div className="mb-5 divide-y divide-line">
                  {variants.map((variant) => (
                    <div key={variant.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                      <div><span className="font-medium">{variant.attribute}: {variant.value}</span><span className="ml-3 num text-muted">{formatMoney(variant.extra_price)}</span>{!variant.is_active && <span className="ml-2 text-xs text-muted">Inactive</span>}</div>
                      {variant.is_active && <div className="flex items-center gap-2"><Button variant="ghost" className="h-8 px-2" onClick={() => startEditVariant(variant)}><Pencil className="h-3.5 w-3.5" /> Edit</Button><Button variant="danger" className="h-8 px-2" onClick={() => void deactivateVariant(variant.id)}><Trash2 className="h-3.5 w-3.5" /> Deactivate</Button></div>}
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="No variants" body="Add optional configurations and their additional prices." />}
              <form onSubmit={(event) => void addVariant(event)} className="grid gap-3 border-t border-line pt-5 md:grid-cols-3">
                <Input label="Attribute" value={variantAttribute} onChange={(event) => setVariantAttribute(event.target.value)} required maxLength={100} />
                <Input label="Value" value={variantValue} onChange={(event) => setVariantValue(event.target.value)} required maxLength={150} />
                <Input label="Extra price (₹)" type="number" min="0" step="0.01" value={variantPrice} onChange={(event) => setVariantPrice(event.target.value)} required />
                <div className="md:col-span-3 flex justify-end"><Button type="submit" loading={saving}>{editingVariantId === null ? "Add variant" : "Save variant"}</Button>{editingVariantId !== null && <Button type="button" variant="secondary" onClick={() => { setEditingVariantId(null); setVariantAttribute(""); setVariantValue(""); setVariantPrice("0"); }}>Cancel edit</Button>}</div>
              </form>
            </div>
          )}
        </Panel>
      )}
    </>
  );
}

"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getAnalysis,
  updateVerification,
  confirmVerification,
  resolvePreviewUrls,
  type AnalyzeResponse,
  type PreviewUrls,
  type VerificationFields,
} from "../../../../lib/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ─── Constants ────────────────────────────────────────────────────────────────

function rm(n: number) {
  return `RM${n.toFixed(2)}`;
}

const COURSE_OPTIONS = [
  { value: "CV",    label: "Civil Engineering" },
  { value: "ME",    label: "Mechanical Engineering" },
  { value: "CE",    label: "Chemical Engineering" },
  { value: "EE",    label: "Electrical Engineering" },
  { value: "ComE",  label: "Computer Engineering" },
  { value: "MAT",   label: "Materials Engineering" },
  { value: "PE",    label: "Petroleum Engineering" },
  { value: "AC",    label: "Applied Chemistry" },
  { value: "OTHER", label: "Other / Unknown" },
] as const;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function VerifyPage({
  params,
}: {
  params: Promise<{ ref: string }>;
}) {
  const { ref } = use(params);
  const router = useRouter();

  // Initial load
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<"expired" | "unknown" | null>(null);
  const [loading, setLoading] = useState(true);

  // Editable fields (init from extraction)
  const [fields, setFields] = useState<VerificationFields>({
    full_name: "",
    thesis_title: "",
    student_id: "",
    course_code: "CV",
    year: "",
  });

  // Preview
  const [previewUrls, setPreviewUrls] = useState<PreviewUrls | null>(null);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [renderVersion, setRenderVersion] = useState(0);
  const [activeTab, setActiveTab] = useState<"hardbound" | "cd">("hardbound");

  // Update / confirm state
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [slipUrl, setSlipUrl] = useState<string | null>(null);

  // Refs for latest values in closures
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isConfirmedRef = useRef(false);
  isConfirmedRef.current = isConfirmed;

  // ── Initial load ─────────────────────────────────────────────────────────

  useEffect(() => {
    getAnalysis(ref)
      .then((result) => {
        setData(result);
        setFields({
          full_name: result.extracted.full_name,
          thesis_title: result.extracted.thesis_title,
          student_id: result.extracted.student_id,
          course_code: result.extracted.course_code,
          year: result.extracted.year,
        });
        if (result.preview_urls) {
          setPreviewUrls(resolvePreviewUrls(result.preview_urls));
          setPreviewFailed(result.preview_failed ?? false);
        }
      })
      .catch((err: Error) => {
        const msg = err.message.toLowerCase();
        if (msg.includes("404") || msg.includes("expired")) {
          setError("expired");
        } else {
          setError("unknown");
        }
      })
      .finally(() => setLoading(false));
  }, [ref]);

  // ── Verification update ───────────────────────────────────────────────────

  const triggerUpdate = useCallback(
    async (currentFields: VerificationFields) => {
      if (isConfirmedRef.current) return;
      setIsUpdating(true);
      setUpdateError(null);
      try {
        const result = await updateVerification(ref, currentFields);
        setPreviewUrls(resolvePreviewUrls(result.preview_urls));
        setPreviewFailed(result.preview_failed);
        setRenderVersion(result.render_version);
      } catch {
        setUpdateError("Preview update failed. Try editing again.");
      } finally {
        setIsUpdating(false);
      }
    },
    [ref]
  );

  // Stable ref so debounce timeout always calls the latest version
  const triggerUpdateRef = useRef(triggerUpdate);
  triggerUpdateRef.current = triggerUpdate;

  const handleFieldChange = (updates: Partial<VerificationFields>) => {
    const newFields = { ...fields, ...updates };
    setFields(newFields);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(
      () => triggerUpdateRef.current(newFields),
      500
    );
  };

  // ── Manual refresh ───────────────────────────────────────────────────────

  const handleManualRefresh = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    triggerUpdateRef.current(fields);
  };

  // ── Confirm ───────────────────────────────────────────────────────────────

  const handleConfirm = async () => {
    if (
      !window.confirm(
        "Once confirmed, you cannot edit these details. Continue?"
      )
    )
      return;
    setIsConfirming(true);
    setUpdateError(null);
    try {
      const result = await confirmVerification(ref);
      setIsConfirmed(true);
      if (result.verification_slip_url) {
        setSlipUrl(`${API_BASE_URL}${result.verification_slip_url}`);
      }
      // No auto-redirect — let the student download the slip first
    } catch {
      setUpdateError("Confirmation failed. Please try again.");
    } finally {
      setIsConfirming(false);
    }
  };

  // ── Derived ───────────────────────────────────────────────────────────────

  const hasCd = (data?.pricing.cd_price ?? 0) > 0;

  const currentPreviewUrl =
    previewUrls &&
    (!hasCd || activeTab === "hardbound"
      ? previewUrls.hardbound_cover
      : previewUrls.cd_case);

  const confirmDisabled =
    loading || isUpdating || isConfirming || isConfirmed || !data;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#F6F5F1] font-sans">
      {/* Header */}
      <header className="bg-[#1B334E] text-white px-6 py-4 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.22em] uppercase text-sky-300">
              SIBC Copy Print
            </p>
            <h1 className="text-base font-semibold mt-0.5 tracking-tight">
              Order Review
            </h1>
          </div>
          <div className="hidden sm:block text-right">
            <p className="text-[11px] text-sky-300">Bandar Seri Iskandar</p>
            <p className="text-[11px] text-sky-300 mt-0.5">+60 12-755 5386</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-24 text-gray-400 text-sm gap-2">
            <SpinnerIcon className="h-5 w-5 animate-spin" />
            Loading your order details…
          </div>
        )}

        {/* Error: expired */}
        {!loading && error === "expired" && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            This analysis has expired or was not found. Please{" "}
            <a href="/order" className="font-semibold underline">
              submit your order again
            </a>
            .
          </div>
        )}

        {/* Error: unknown */}
        {!loading && error === "unknown" && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            Something went wrong loading your order. Try again or{" "}
            <a href="/order" className="font-semibold underline">
              start over
            </a>
            .
          </div>
        )}

        {/* Main two-column layout */}
        {!loading && data && (
          <div className="lg:grid lg:grid-cols-5 lg:gap-8 space-y-6 lg:space-y-0">
            {/* ── Left column ─────────────────────────────────────────── */}
            <div className="lg:col-span-2 space-y-6">
              {/* Step indicator */}
              <p className="text-xs text-gray-500 tracking-wide uppercase">
                Step 2 of 4 — Verify Details
              </p>

              {/* Low-confidence banner */}
              {data.extracted.confidence === "low" && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Some fields could not be confirmed automatically. Please
                  review and correct them below.
                </div>
              )}

              {/* Editable fields */}
              <Section title="Edit Details">
                <div className="space-y-4">
                  <FieldGroup label="Thesis Title">
                    <textarea
                      rows={3}
                      value={fields.thesis_title}
                      onChange={(e) =>
                        handleFieldChange({ thesis_title: e.target.value })
                      }
                      disabled={isConfirmed}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 leading-snug resize-none focus:outline-none focus:ring-2 focus:ring-[#1B334E]/20 focus:border-[#1B334E] disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
                    />
                  </FieldGroup>

                  <FieldGroup label="Full Name">
                    <input
                      type="text"
                      value={fields.full_name}
                      onChange={(e) =>
                        handleFieldChange({ full_name: e.target.value })
                      }
                      disabled={isConfirmed}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1B334E]/20 focus:border-[#1B334E] disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
                    />
                  </FieldGroup>

                  <FieldGroup label="Student ID">
                    <input
                      type="text"
                      value={fields.student_id}
                      onChange={(e) =>
                        handleFieldChange({ student_id: e.target.value })
                      }
                      disabled={isConfirmed}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1B334E]/20 focus:border-[#1B334E] disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
                    />
                  </FieldGroup>

                  <FieldGroup label="Course">
                    <select
                      value={fields.course_code}
                      onChange={(e) =>
                        handleFieldChange({ course_code: e.target.value })
                      }
                      disabled={isConfirmed}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#1B334E]/20 focus:border-[#1B334E] disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
                    >
                      {COURSE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </FieldGroup>

                  <FieldGroup label="Graduation Month & Year">
                    <input
                      type="text"
                      value={fields.year}
                      placeholder="e.g. JAN 2026"
                      onChange={(e) =>
                        handleFieldChange({ year: e.target.value })
                      }
                      disabled={isConfirmed}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#1B334E]/20 focus:border-[#1B334E] disabled:bg-gray-50 disabled:text-gray-500 transition-colors"
                    />
                  </FieldGroup>
                </div>
              </Section>

              {/* Shipping Address (read-only, only when present) */}
              {data.shipping_address && (
                <Section title="Shipping Address">
                  <p className="text-sm text-gray-800 whitespace-pre-line leading-relaxed">
                    {data.shipping_address}
                  </p>
                </Section>
              )}

              {/* Page Analysis */}
              <Section title="Page Analysis">
                <div className="grid grid-cols-3 gap-3">
                  <Stat label="Total" value={String(data.pages.total_pages)} />
                  <Stat
                    label="B&W"
                    value={String(data.pages.bw_pages)}
                    sub={`× RM0.10 = ${rm(data.pages.bw_pages * 0.1)}`}
                  />
                  <Stat
                    label="Colour"
                    value={String(data.pages.color_pages)}
                    sub={`× RM0.30 = ${rm(data.pages.color_pages * 0.3)}`}
                  />
                </div>
                {data.pages.color_page_numbers.length > 0 && (
                  <p className="mt-3 text-xs text-gray-500 leading-relaxed">
                    Colour pages:{" "}
                    <span className="text-gray-700 tabular-nums">
                      {data.pages.color_page_numbers.join(", ")}
                    </span>
                  </p>
                )}
              </Section>

              {/* Price Breakdown */}
              <div className="rounded-xl bg-[#1B334E] p-5 text-white">
                <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-sky-300 mb-4">
                  Price Breakdown
                </p>
                <div className="space-y-2.5 text-sm">
                  <PriceRow
                    label="Hardbound cover"
                    value={rm(data.pricing.cover_price)}
                  />
                  <PriceRow
                    label={`B&W printing (${data.pages.bw_pages} pages)`}
                    value={rm(data.pricing.bw_print_price)}
                  />
                  {data.pages.color_pages > 0 && (
                    <PriceRow
                      label={`Colour printing (${data.pages.color_pages} pages)`}
                      value={rm(data.pricing.color_print_price)}
                    />
                  )}
                  {data.pricing.cd_price > 0 && (
                    <PriceRow label="CD" value={rm(data.pricing.cd_price)} />
                  )}
                  <PriceRow
                    label="Delivery"
                    value={
                      data.pricing.delivery_price === 0
                        ? "Free"
                        : rm(data.pricing.delivery_price)
                    }
                    free={data.pricing.delivery_price === 0}
                  />
                  {data.pricing.fast_track_price > 0 && (
                    <PriceRow
                      label="Fast Track"
                      value={rm(data.pricing.fast_track_price)}
                    />
                  )}
                  <div className="border-t border-white/20 pt-3 flex items-baseline justify-between">
                    <span className="font-semibold text-white/90">
                      Grand Total
                    </span>
                    <span className="text-2xl font-bold tabular-nums">
                      {rm(data.pricing.grand_total)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Slot Allocation */}
              <Section title="Slot Allocation">
                <div className="flex items-center gap-6 text-sm text-gray-700">
                  <div>
                    <p className="text-[11px] text-gray-400 mb-0.5">
                      Allocated date
                    </p>
                    <p className="font-medium">
                      {data.slot_preview.allocated_date}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-gray-400 mb-0.5">
                      Remaining slots
                    </p>
                    <p className="font-medium">
                      {data.slot_preview.remaining_capacity}
                    </p>
                  </div>
                  {data.slot_preview.cutoff_applied && (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                      Next-day slot (cutoff applied)
                    </p>
                  )}
                </div>
              </Section>

              {/* Confirm button / success card */}
              <div className="pt-2 pb-8">
                {isConfirmed ? (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 space-y-4">
                    <div className="flex items-start gap-3">
                      <CheckCircleIcon className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-emerald-800">
                          Verification confirmed
                        </p>
                        <p className="text-xs text-emerald-700 mt-0.5">
                          Save the slip below — it's your proof of approved details.
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      {slipUrl ? (
                        <a
                          href={slipUrl}
                          download={`verification-slip-${ref}.pdf`}
                          className="w-full rounded-lg py-3 text-sm font-semibold text-center flex items-center justify-center gap-2 bg-[#1B334E] text-white hover:bg-[#162840] transition-colors"
                        >
                          <DownloadIcon className="h-4 w-4" />
                          Download Verification Slip
                        </a>
                      ) : (
                        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                          Slip generation failed — contact the shop with your Analysis ID:{" "}
                          <span className="font-mono font-semibold">{ref}</span>
                        </p>
                      )}
                      <button
                        onClick={() => router.push(`/order/payment/${ref}`)}
                        className="w-full rounded-lg py-3 text-sm font-semibold border border-[#1B334E] text-[#1B334E] hover:bg-[#1B334E]/5 transition-colors"
                      >
                        Continue to Payment
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={handleConfirm}
                    disabled={confirmDisabled}
                    className={`w-full rounded-lg py-3.5 text-sm font-semibold tracking-wide flex items-center justify-center gap-2 transition-colors ${
                      confirmDisabled
                        ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                        : "bg-[#1B334E] text-white hover:bg-[#162840] active:bg-[#0f1e2e]"
                    }`}
                  >
                    {isConfirming && (
                      <SpinnerIcon className="h-4 w-4 animate-spin" />
                    )}
                    Confirm Verification
                  </button>
                )}
              </div>
            </div>

            {/* ── Right column: PDF Preview ─────────────────────────────── */}
            <div className="lg:col-span-3 lg:sticky lg:top-8 lg:self-start">
              <div className="rounded-xl bg-white border border-gray-200 overflow-hidden">
                {/* Panel header */}
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between min-h-[56px]">
                  <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#1B334E]">
                    Template Preview
                  </p>
                  <div className="flex items-center gap-2">
                    {isUpdating && (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 border border-sky-200 px-2.5 py-0.5 text-[11px] text-sky-700 shrink-0">
                        <SpinnerIcon className="h-3 w-3 animate-spin" />
                        Updating preview…
                      </span>
                    )}
                    {updateError && !isUpdating && (
                      <span className="text-[11px] text-red-600 text-right leading-snug max-w-[180px]">
                        {updateError}
                      </span>
                    )}
                    <button
                      onClick={handleManualRefresh}
                      disabled={loading || isUpdating || isConfirming || isConfirmed || !data}
                      aria-label="Refresh preview"
                      title="Refresh preview"
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-2.5 py-0.5 text-[11px] font-medium text-[#1B334E] transition-colors hover:border-[#1B334E] hover:bg-[#1B334E]/5 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <RefreshIcon className="h-3 w-3 shrink-0" />
                      Refresh preview
                    </button>
                  </div>
                </div>

                {/* Tab switcher */}
                <div className="px-5 pt-3 pb-1 flex gap-2">
                  <TabButton
                    active={activeTab === "hardbound"}
                    onClick={() => setActiveTab("hardbound")}
                  >
                    Hardbound Cover
                  </TabButton>
                  {hasCd && (
                    <TabButton
                      active={activeTab === "cd"}
                      onClick={() => setActiveTab("cd")}
                    >
                      CD Case
                    </TabButton>
                  )}
                </div>

                {/* Preview area */}
                <div className="p-4">
                  {previewFailed ? (
                    <FallbackDownload previewUrls={previewUrls} hasCd={hasCd} />
                  ) : currentPreviewUrl ? (
                    <iframe
                      key={`${activeTab}-v${renderVersion}`}
                      src={currentPreviewUrl}
                      className="w-full rounded-lg border border-gray-100"
                      style={{ height: "560px" }}
                      title={
                        activeTab === "hardbound"
                          ? "Hardbound Cover Preview"
                          : "CD Case Preview"
                      }
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 rounded-lg bg-gray-50 border border-gray-100 gap-3 text-center px-4">
                      <SpinnerIcon className="h-6 w-6 text-gray-300 animate-spin" />
                      <p className="text-sm text-gray-400">
                        Generating preview…
                      </p>
                      <p className="text-xs text-gray-400">
                        This takes a few seconds on first load.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-white border border-gray-200 p-5">
      <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#1B334E] mb-4">
        {title}
      </p>
      {children}
    </div>
  );
}

function FieldGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-3 text-center">
      <p className="text-2xl font-bold text-[#1B334E] tabular-nums">{value}</p>
      <p className="text-xs font-medium text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function PriceRow({
  label,
  value,
  free = false,
}: {
  label: string;
  value: string;
  free?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-white/80 text-sm">{label}</span>
      <span
        className={`tabular-nums font-medium text-sm shrink-0 ${
          free ? "text-emerald-400" : "text-white/90"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
        active
          ? "bg-[#1B334E] text-white"
          : "bg-gray-100 text-gray-500 hover:bg-gray-200"
      }`}
    >
      {children}
    </button>
  );
}

function FallbackDownload({
  previewUrls,
  hasCd,
}: {
  previewUrls: PreviewUrls | null;
  hasCd: boolean;
}) {
  return (
    <div className="rounded-lg bg-amber-50 border border-amber-200 p-5 text-sm">
      <p className="text-amber-800 font-medium mb-1">Preview generation failed</p>
      <p className="text-amber-700 text-xs mb-4">
        Download the filled templates to review offline.
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <a
          href={previewUrls?.hardbound_cover_docx ?? "#"}
          download="hardbound_cover.docx"
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-amber-300 bg-white px-4 py-2 text-xs font-semibold text-amber-800 hover:bg-amber-50 transition-colors"
        >
          <DownloadIcon className="h-3.5 w-3.5" />
          Hardbound Cover (.docx)
        </a>
        {hasCd && (
          <a
            href={previewUrls?.cd_case_docx ?? "#"}
            download="cd_case.docx"
            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-amber-300 bg-white px-4 py-2 text-xs font-semibold text-amber-800 hover:bg-amber-50 transition-colors"
          >
            <DownloadIcon className="h-3.5 w-3.5" />
            CD Case (.docx)
          </a>
        )}
      </div>
    </div>
  );
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

"use client";

import { use, useEffect, useState } from "react";
import { getAnalysis, type AnalyzeResponse } from "../../../../lib/api";

function rm(n: number) {
  return `RM${n.toFixed(2)}`;
}

const COURSE_LABELS: Record<string, string> = {
  CV: "Civil Engineering",
  ME: "Mechanical Engineering",
  CE: "Chemical Engineering",
  EE: "Electrical Engineering",
  ComE: "Computer Engineering",
  MAT: "Materials Engineering",
  PE: "Petroleum Engineering",
  AC: "Applied Chemistry",
  OTHER: "Other / Unknown",
};

export default function VerifyPage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = use(params);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<"expired" | "unknown" | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalysis(ref)
      .then(setData)
      .catch((err: Error) => {
        if (err.message.includes("404") || err.message.toLowerCase().includes("expired")) {
          setError("expired");
        } else {
          setError("unknown");
        }
      })
      .finally(() => setLoading(false));
  }, [ref]);

  return (
    <div className="min-h-screen bg-[#F6F5F1] font-sans">
      <header className="bg-[#1B334E] text-white px-6 py-4 shadow-sm">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
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

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="flex items-center justify-center py-24 text-gray-400 text-sm gap-2">
            <SpinnerIcon className="h-5 w-5 animate-spin" />
            Loading your order details…
          </div>
        )}

        {!loading && error === "expired" && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            This analysis has expired or was not found. Please{" "}
            <a href="/order" className="font-semibold underline">
              submit your order again
            </a>
            .
          </div>
        )}

        {!loading && error === "unknown" && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            Something went wrong loading your order. Try again or{" "}
            <a href="/order" className="font-semibold underline">
              start over
            </a>
            .
          </div>
        )}

        {!loading && data && (
          <div className="space-y-6">
            {/* Step indicator */}
            <p className="text-xs text-gray-500 tracking-wide uppercase">
              Step 2 of 4 — Review extracted details
            </p>

            {/* Low-confidence banner */}
            {data.extracted.confidence === "low" && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Some fields could not be confirmed automatically. You will be able to edit them in the next step.
              </div>
            )}

            {/* Extracted fields */}
            <Section title="Extracted from PDF">
              <dl className="divide-y divide-gray-100">
                <Row label="Thesis Title" value={data.extracted.thesis_title || "—"} />
                <Row label="Full Name" value={data.extracted.full_name || "—"} />
                <Row label="Student ID" value={data.extracted.student_id || "—"} />
                <Row
                  label="Course"
                  value={
                    COURSE_LABELS[data.extracted.course_code] ||
                    data.extracted.course_code
                  }
                />
                <Row label="Degree" value={data.extracted.degree || "—"} />
                <Row label="Graduation" value={data.extracted.year || "—"} />
                <Row
                  label="Project Type"
                  value={data.extracted.project_type === "FYP" ? "FYP (Undergraduate)" : "Postgraduate"}
                />
              </dl>
              <p className="mt-3 text-[11px] text-gray-400">
                Extracted via {data.extracted.extraction_method} · confidence:{" "}
                <span
                  className={
                    data.extracted.confidence === "high"
                      ? "text-emerald-600"
                      : "text-amber-600"
                  }
                >
                  {data.extracted.confidence}
                </span>
              </p>
            </Section>

            {/* Page analysis */}
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

            {/* Price breakdown */}
            <div className="rounded-xl bg-[#1B334E] p-5 text-white">
              <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-sky-300 mb-4">
                Price Breakdown
              </p>
              <div className="space-y-2.5 text-sm">
                <PriceRow label="Hardbound cover" value={rm(data.pricing.cover_price)} />
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
                  value={data.pricing.delivery_price === 0 ? "Free" : rm(data.pricing.delivery_price)}
                  free={data.pricing.delivery_price === 0}
                />
                {data.pricing.fast_track_price > 0 && (
                  <PriceRow label="Fast Track" value={rm(data.pricing.fast_track_price)} />
                )}
                <div className="border-t border-white/20 pt-3 flex items-baseline justify-between">
                  <span className="font-semibold text-white/90">Grand Total</span>
                  <span className="text-2xl font-bold tabular-nums">
                    {rm(data.pricing.grand_total)}
                  </span>
                </div>
              </div>
            </div>

            {/* Slot preview */}
            <Section title="Slot Allocation">
              <div className="flex items-center gap-6 text-sm text-gray-700">
                <div>
                  <p className="text-[11px] text-gray-400 mb-0.5">Allocated date</p>
                  <p className="font-medium">{data.slot_preview.allocated_date}</p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400 mb-0.5">Remaining slots</p>
                  <p className="font-medium">{data.slot_preview.remaining_capacity}</p>
                </div>
                {data.slot_preview.cutoff_applied && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    Next-day slot (cutoff applied)
                  </p>
                )}
              </div>
            </Section>

            {/* Continue button */}
            <div className="pt-2">
              <button
                disabled
                title="Field editing and cover preview are available in the next update"
                className="w-full rounded-lg py-3.5 text-sm font-semibold tracking-wide bg-gray-200 text-gray-400 cursor-not-allowed"
              >
                Continue to Verification
              </button>
              <p className="mt-2 text-center text-xs text-gray-400">
                Field editing and cover preview coming in the next step — please check back soon.
              </p>
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-2.5 sm:grid sm:grid-cols-3 sm:gap-4">
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 sm:mt-0 sm:col-span-2 text-sm text-gray-900 leading-snug">
        {value}
      </dd>
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

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  getAvailability,
  analyzeOrder,
  type AvailabilityResponse,
} from "../../lib/api";

// ─── Constants ────────────────────────────────────────────────────────────────

const DELIVERY_OPTIONS = [
  { value: "SELF_PICKUP", label: "Self Pickup", price: 0 },
  { value: "UTP_DELIVERY", label: "Delivery to UTP", price: 5 },
  { value: "POSTAGE_SEMENANJUNG", label: "Postage — Semenanjung", price: 10 },
  { value: "POSTAGE_SABAH_SARAWAK", label: "Postage — Sabah / Sarawak", price: 35 },
  { value: "POSTAGE_INTERNATIONAL", label: "Postage — International", price: 100 },
] as const;

const COVER_PRICE = 36.0;
const CD_PRICE = 4.0;
const FAST_TRACK_PRICE = 10.0;
const MAX_FILE_BYTES = 30 * 1024 * 1024;

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z.object({
  full_name: z.string().min(1, "Full name is required"),
  email: z.string().email("Enter a valid email"),
  phone: z.string().min(1, "Phone number is required"),
  student_id: z.string().min(1, "Student ID is required"),
  num_hardbound: z.number().int().min(1, "At least 1 required"),
  num_cd: z.number().int().min(0, "Cannot be negative"),
  delivery_option: z.enum([
    "SELF_PICKUP",
    "UTP_DELIVERY",
    "POSTAGE_SEMENANJUNG",
    "POSTAGE_SABAH_SARAWAK",
    "POSTAGE_INTERNATIONAL",
  ]),
  fast_track: z.boolean().default(false),
  shipping_address: z.string().optional(),
}).superRefine((val, ctx) => {
  const needsAddress = val.delivery_option === "UTP_DELIVERY" ||
    val.delivery_option.startsWith("POSTAGE_");
  const minLen = val.delivery_option === "UTP_DELIVERY" ? 1 : 5;
  if (needsAddress && (!val.shipping_address || val.shipping_address.trim().length < minLen)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: val.delivery_option === "UTP_DELIVERY"
        ? "Delivery location is required"
        : "Shipping address is required (min 5 characters)",
      path: ["shipping_address"],
    });
  }
});

type FormValues = z.infer<typeof schema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toE164(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.startsWith("60")) return `+${digits}`;
  if (digits.startsWith("0")) return `+6${digits}`;
  return `+60${digits}`;
}

function rm(amount: number): string {
  return `RM${amount.toFixed(2)}`;
}

function getMalaysiaHour(): number {
  return new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Kuala_Lumpur" })
  ).getHours();
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OrderPage() {
  const router = useRouter();

  const [availability, setAvailability] = useState<AvailabilityResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors, isValid },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      num_hardbound: 1,
      num_cd: 0,
      delivery_option: "SELF_PICKUP",
      fast_track: false,
    },
    mode: "onChange",
  });

  const [numHardbound, numCd, deliveryOption, fastTrack] = watch([
    "num_hardbound",
    "num_cd",
    "delivery_option",
    "fast_track",
  ]);

  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];
    getAvailability(today).then(setAvailability).catch(console.error);
  }, []);

  const isCutoffTime = getMalaysiaHour() >= 23;
  const isSlotsEmpty = availability?.remaining_capacity === 0;

  // Live price calculation
  const deliveryPrice =
    DELIVERY_OPTIONS.find((d) => d.value === deliveryOption)?.price ?? 0;
  const coverTotal = (Number(numHardbound) || 0) * COVER_PRICE;
  const cdTotal = (Number(numCd) || 0) * CD_PRICE;
  const fastTrackTotal = fastTrack ? FAST_TRACK_PRICE : 0;
  const subtotal = coverTotal + cdTotal + deliveryPrice + fastTrackTotal;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setFileError("");
    if (!file) {
      setSelectedFile(null);
      return;
    }
    if (file.type !== "application/pdf") {
      setFileError("Only PDF files are accepted");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setFileError("File must be under 30 MB");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }
    setSelectedFile(file);
  }

  const onSubmit = async (data: FormValues) => {
    if (!selectedFile) {
      setFileError("Please upload your thesis PDF");
      return;
    }
    setSubmitError("");
    setIsSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("thesis_pdf", selectedFile);
      fd.append("full_name", data.full_name);
      fd.append("email", data.email);
      fd.append("phone", toE164(data.phone));
      fd.append("student_id", data.student_id);
      fd.append("num_hardbound", String(data.num_hardbound));
      fd.append("num_cd", String(data.num_cd));
      fd.append("delivery_option", data.delivery_option);
      fd.append("fast_track", String(data.fast_track));
      if (data.shipping_address) fd.append("shipping_address", data.shipping_address);
      const result = await analyzeOrder(fd);
      router.push(`/order/verify/${result.analysis_id}`);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Something went wrong. Try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit =
    isValid && !!selectedFile && !isSubmitting && !isCutoffTime && !isSlotsEmpty;

  const selectedDeliveryLabel =
    DELIVERY_OPTIONS.find((d) => d.value === deliveryOption)?.label ?? "";

  return (
    <div className="min-h-screen bg-[#F6F5F1] font-sans">
      {/* ── Header ── */}
      <header className="bg-[#1B334E] text-white px-6 py-4 shadow-sm">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.22em] uppercase text-sky-300">
              SIBC Copy Print
            </p>
            <h1 className="text-base font-semibold mt-0.5 tracking-tight">
              Hardbound Thesis Order
            </h1>
          </div>
          <div className="hidden sm:block text-right">
            <p className="text-[11px] text-sky-300">Bandar Seri Iskandar</p>
            <p className="text-[11px] text-sky-300 mt-0.5">+60 12-755 5386</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ── Banners ── */}
        {isCutoffTime && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Orders close at 11 PM. Come back tomorrow to submit your order.
          </div>
        )}
        {isSlotsEmpty && !isCutoffTime && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            Today&apos;s slots are full.
            {availability?.next_available_date && (
              <>
                {" "}
                Next available date:{" "}
                <strong>{availability.next_available_date}</strong>.
              </>
            )}
          </div>
        )}

        {/* ── Two-column layout ── */}
        <div className="lg:grid lg:grid-cols-[1fr_300px] lg:gap-10 items-start">
          {/* ── Form ── */}
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-9">
            {/* Student Info */}
            <section>
              <SectionLabel>Student Information</SectionLabel>
              <div className="grid sm:grid-cols-2 gap-x-4 gap-y-4 mt-5">
                <Field
                  label="Name"
                  error={errors.full_name?.message}
                  className="sm:col-span-2"
                >
                  <input
                    {...register("full_name")}
                    type="text"
                    placeholder="your name"
                    className={input(!!errors.full_name)}
                  />
                </Field>
                <Field label="Email" error={errors.email?.message}>
                  <input
                    {...register("email")}
                    type="email"
                    placeholder="your personal email address"
                    className={input(!!errors.email)}
                  />
                </Field>
                <Field label="Phone Number" error={errors.phone?.message}>
                  <input
                    {...register("phone")}
                    type="tel"
                    placeholder="011-1234 5678"
                    className={input(!!errors.phone)}
                  />
                </Field>
                <Field label="Student ID" error={errors.student_id?.message}>
                  <input
                    {...register("student_id")}
                    type="text"
                    placeholder="e.g. 21000201"
                    className={input(!!errors.student_id)}
                  />
                </Field>
              </div>
            </section>

            {/* Thesis Upload */}
            <section>
              <SectionLabel>Thesis PDF</SectionLabel>
              <div className="mt-5">
                <label
                  className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-8 text-center cursor-pointer transition-colors ${
                    fileError
                      ? "border-red-300 bg-red-50"
                      : selectedFile
                      ? "border-emerald-400 bg-emerald-50"
                      : "border-gray-300 bg-white hover:border-[#1B334E] hover:bg-sky-50"
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={handleFileChange}
                    className="sr-only"
                  />
                  {selectedFile ? (
                    <>
                      <CheckCircleIcon className="h-9 w-9 text-emerald-500" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {selectedFile.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                        </p>
                      </div>
                      <p className="text-xs text-sky-600">Click to change file</p>
                    </>
                  ) : (
                    <>
                      <UploadIcon className="h-10 w-10 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-700">
                          Click to upload your thesis
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          PDF only · Max 30 MB
                        </p>
                      </div>
                    </>
                  )}
                </label>
                {fileError && (
                  <p className="mt-1.5 text-xs text-red-600">{fileError}</p>
                )}
              </div>
            </section>

            {/* Order Options */}
            <section>
              <SectionLabel>Order Options</SectionLabel>
              <div className="mt-5 space-y-5">
                {/* Counts */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <Field
                    label="Hardbound Copies"
                    error={errors.num_hardbound?.message}
                  >
                    <input
                      {...register("num_hardbound", { valueAsNumber: true })}
                      type="number"
                      min={1}
                      className={input(!!errors.num_hardbound)}
                    />
                  </Field>
                  <Field
                    label="CD Copies"
                    error={errors.num_cd?.message}
                  >
                    <input
                      {...register("num_cd", { valueAsNumber: true })}
                      type="number"
                      min={0}
                      className={input(!!errors.num_cd)}
                    />
                  </Field>
                </div>

                {/* Delivery */}
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2.5">
                    Delivery Option
                  </p>
                  <div className="space-y-2">
                    {DELIVERY_OPTIONS.map((opt) => {
                      const selected = watch("delivery_option") === opt.value;
                      return (
                        <label
                          key={opt.value}
                          className={`flex items-center justify-between rounded-lg border px-4 py-3 cursor-pointer transition-all ${
                            selected
                              ? "border-[#1B334E] bg-[#1B334E]/5 ring-1 ring-[#1B334E]/20"
                              : "border-gray-200 bg-white hover:border-gray-300"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <input
                              {...register("delivery_option")}
                              type="radio"
                              value={opt.value}
                              className="text-[#1B334E] focus:ring-[#1B334E] h-4 w-4"
                            />
                            <span className="text-sm text-gray-800">
                              {opt.label}
                            </span>
                          </div>
                          <span className="text-sm font-semibold text-gray-700 tabular-nums">
                            {opt.price === 0 ? (
                              <span className="text-emerald-600">Free</span>
                            ) : (
                              rm(opt.price)
                            )}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                {/* Conditional address field */}
                {deliveryOption === "UTP_DELIVERY" && (
                  <Field
                    label="Delivery Location"
                    error={errors.shipping_address?.message}
                  >
                    <input
                      {...register("shipping_address")}
                      type="text"
                      placeholder="UTP Academic Complex / Pigeon Hole / Hostel or Village / etc.,"
                      className={input(!!errors.shipping_address)}
                    />
                  </Field>
                )}
                {(deliveryOption === "POSTAGE_SEMENANJUNG" ||
                  deliveryOption === "POSTAGE_SABAH_SARAWAK") && (
                  <Field
                    label="Shipping Address"
                    error={errors.shipping_address?.message}
                  >
                    <textarea
                      {...register("shipping_address")}
                      rows={4}
                      placeholder={"Full mailing address — street, postcode, state"}
                      className={input(!!errors.shipping_address)}
                    />
                  </Field>
                )}
                {deliveryOption === "POSTAGE_INTERNATIONAL" && (
                  <Field
                    label="Shipping Address"
                    error={errors.shipping_address?.message}
                  >
                    <textarea
                      {...register("shipping_address")}
                      rows={4}
                      placeholder={"Full mailing address — street, postcode, state, country"}
                      className={input(!!errors.shipping_address)}
                    />
                  </Field>
                )}

                {/* Fast Track */}
                <label className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-4 cursor-pointer hover:border-amber-300 transition-colors">
                  <div>
                    <p className="text-sm font-medium text-gray-800">
                      Fast Track Processing
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Priority queue · +RM10.00 per order
                    </p>
                  </div>
                  <Controller
                    name="fast_track"
                    control={control}
                    render={({ field }) => (
                      <button
                        type="button"
                        role="switch"
                        aria-checked={field.value}
                        onClick={() => field.onChange(!field.value)}
                        className={`relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 ${
                          field.value ? "bg-amber-400" : "bg-gray-200"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
                            field.value ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    )}
                  />
                </label>
              </div>
            </section>

            {/* Mobile price summary */}
            <div className="lg:hidden">
              <PriceSummary
                numHardbound={Number(numHardbound) || 0}
                numCd={Number(numCd) || 0}
                coverTotal={coverTotal}
                cdTotal={cdTotal}
                deliveryLabel={selectedDeliveryLabel}
                deliveryPrice={deliveryPrice}
                fastTrackTotal={fastTrackTotal}
                subtotal={subtotal}
              />
            </div>

            {/* Submit */}
            {submitError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {submitError}
              </div>
            )}

            <button
              type="submit"
              disabled={!canSubmit}
              className={`w-full rounded-lg py-3.5 text-sm font-semibold tracking-wide transition-all ${
                canSubmit
                  ? "bg-[#1B334E] text-white hover:bg-[#152840] active:scale-[0.99]"
                  : "cursor-not-allowed bg-gray-200 text-gray-400"
              }`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <SpinnerIcon className="h-4 w-4 animate-spin" />
                  Analysing PDF…
                </span>
              ) : (
                "Submit Order"
              )}
            </button>
          </form>

          {/* Desktop sticky price summary */}
          <aside className="hidden lg:block sticky top-6">
            <PriceSummary
              numHardbound={Number(numHardbound) || 0}
              numCd={Number(numCd) || 0}
              coverTotal={coverTotal}
              cdTotal={cdTotal}
              deliveryLabel={selectedDeliveryLabel}
              deliveryPrice={deliveryPrice}
              fastTrackTotal={fastTrackTotal}
              subtotal={subtotal}
            />
          </aside>
        </div>
      </main>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#1B334E]">
        {children}
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  );
}

function Field({
  label,
  error,
  children,
  className = "",
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">
        {label}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function input(hasError: boolean) {
  return `w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 bg-white outline-none transition-colors ${
    hasError
      ? "border-red-300 focus:border-red-400 focus:ring-2 focus:ring-red-100"
      : "border-gray-300 focus:border-[#1B334E] focus:ring-2 focus:ring-[#1B334E]/10"
  }`;
}

interface PriceSummaryProps {
  numHardbound: number;
  numCd: number;
  coverTotal: number;
  cdTotal: number;
  deliveryLabel: string;
  deliveryPrice: number;
  fastTrackTotal: number;
  subtotal: number;
}

function PriceSummary({
  numHardbound,
  numCd,
  coverTotal,
  cdTotal,
  deliveryLabel,
  deliveryPrice,
  fastTrackTotal,
  subtotal,
}: PriceSummaryProps) {
  return (
    <div className="rounded-xl bg-[#1B334E] p-5 text-white">
      <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-sky-300 mb-4">
        Order Summary
      </p>

      <div className="space-y-3 text-sm">
        <Row
          label={`Hardbound × ${numHardbound}`}
          sub="RM36.00 each"
          value={rm(coverTotal)}
        />
        {numCd > 0 && (
          <Row
            label={`CD × ${numCd}`}
            sub="RM4.00 each"
            value={rm(cdTotal)}
          />
        )}
        <Row
          label={deliveryLabel || "Delivery"}
          value={deliveryPrice === 0 ? "Free" : rm(deliveryPrice)}
          freeValue={deliveryPrice === 0}
        />
        {fastTrackTotal > 0 && (
          <Row label="Fast Track" value={rm(fastTrackTotal)} />
        )}

        <div className="border-t border-white/20 pt-3">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold text-white/90">Partial Estimate</span>
            <span className="text-xl font-bold tabular-nums">{rm(subtotal)}</span>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-lg bg-amber-400 px-3 py-3 flex items-start gap-2">
        <span className="text-amber-900 font-bold text-sm shrink-0 mt-px">⚠</span>
        <p className="text-xs font-semibold text-amber-900 leading-snug">
          Page printing costs not included. B&amp;W and colour costs are added after your PDF is reviewed — final price shown on the next step.
        </p>
      </div>
    </div>
  );
}

function Row({
  label,
  sub,
  value,
  freeValue = false,
}: {
  label: string;
  sub?: string;
  value: string;
  freeValue?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <p className="text-white/90 truncate">{label}</p>
        {sub && <p className="text-[11px] text-sky-300">{sub}</p>}
      </div>
      <span
        className={`shrink-0 tabular-nums font-medium ${
          freeValue ? "text-emerald-400" : "text-white/90"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
      />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
      />
    </svg>
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

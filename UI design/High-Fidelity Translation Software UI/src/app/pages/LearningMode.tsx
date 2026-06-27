import { useEffect, useState } from "react";
import { Archive, FolderUp, Sparkles, Info, Check, Plus, Play, Bot, Gem, Wrench } from "lucide-react";
import { BotAvatar } from "../components/Sidebar";
import { get_capabilities } from "../../contracts/capability_map";
import { get_self_decision_status } from "../../contracts/backend_bridge";
import type { SelfDecisionStatusDTO } from "../../contracts/learning_strategy";

const DEFAULT_SELF_DECISION: SelfDecisionStatusDTO = {
  eligible: false,
  reason: "missing_validation",
  risk_level: "high",
  requires_ai_collaboration: true,
  requires_human_confirmation: true,
  rollback_supported: true,
};

const learningSteps = [
  { title: "Training set", desc: "Waiting for a desktop-selected training set", state: "Waiting" },
  { title: "Validation set", desc: "Waiting for a desktop-selected validation set", state: "Waiting" },
  { title: "Human review", desc: "Required before writeback", state: "Waiting" },
  { title: "Self-decision gate", desc: "Evaluated by capability eligibility", state: "Waiting" },
];

function LearningMessage({ title, subtitle, file, size, status, meta, time, success = false }: any) {
  return (
    <div className="flex items-start gap-3">
      <BotAvatar />
      <div className="flex-1 rounded-3xl border bg-card p-4 shadow-sm">
        <div className="font-bold">{title}</div>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        <div className="mt-4 flex items-center gap-3 rounded-2xl border bg-input-background p-3">
          <div className="grid size-10 place-items-center rounded-xl bg-blue-600 text-white">
            <Archive size={20} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold">{file}</div>
            <div className="text-xs text-muted-foreground">{size}</div>
          </div>
          <button
            disabled
            title="Learning files are selected through the Windows backend workbench."
            className={`rounded-xl px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${success ? "text-emerald-600" : "border border-dashed border-primary text-primary"}`}
          >
            {success ? <Check size={16} className="mr-1 inline" /> : <Plus size={16} className="mr-1 inline" />}
            {status}
          </button>
        </div>
        <div className="mt-3 flex justify-between text-xs text-muted-foreground">
          <span>{meta}</span>
          <span>{time}</span>
        </div>
      </div>
    </div>
  );
}

function TrainingProgress() {
  return (
    <div className="flex items-start gap-3">
      <BotAvatar />
      <div className="flex-1 rounded-3xl border bg-card p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="font-bold">Learning state</div>
          <div className="text-sm font-semibold text-muted-foreground">idle</div>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-4">
          {learningSteps.map((s, i) => (
            <div key={s.title} className="relative text-center">
              <div
                className={`mx-auto grid size-7 place-items-center rounded-full ${
                  s.state === "Completed"
                    ? "bg-primary text-white"
                    : s.state === "In progress"
                    ? "border-2 border-primary bg-white text-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {s.state === "Completed" ? <Check size={15} /> : i + 1}
              </div>
              <div className="mt-2 text-sm font-semibold">{s.title}</div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{s.desc}</p>
              <div
                className={`mt-2 text-xs font-semibold ${
                  s.state === "Completed" ? "text-emerald-600" : s.state === "In progress" ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {s.state}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Metric({ title, value, sub, color }: any) {
  return (
    <div className="mt-5 rounded-2xl border p-4">
      <div className="text-sm font-bold">{title}</div>
      <div className={`mt-3 text-4xl font-bold ${color}`}>{value}</div>
      <p className="mt-2 text-sm text-muted-foreground">{sub}</p>
    </div>
  );
}

function LearningInsight() {
  return (
    <aside className="hidden w-[300px] shrink-0 border-l bg-card p-5 xl:block overflow-y-auto">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Gem className="text-primary" />
        Insights / decisions
      </h2>
      <Metric title="Terminology consistency" value="Waiting" sub="Available after backend LearningState produces reviewed data." color="text-muted-foreground" />
      <Metric title="Human review gate" value="Required" sub="FinalizeService.confirm_run is required before writeback." color="text-primary" />
      <div className="mt-5 rounded-2xl border p-4">
        <div className="text-sm font-bold">Branch cases</div>
        <div className="mt-3 text-3xl font-bold">
          Pending<span className="text-base text-muted-foreground"> cases</span>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">Branch details load only from backend learning results.</p>
        <button disabled className="mt-3 w-full rounded-xl border py-2 text-sm text-primary hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">View branch details</button>
      </div>
      <div className="mt-5">
        <h3 className="flex items-center gap-2 font-bold">
          <Wrench size={18} className="text-primary" />
          Capability-gated actions
        </h3>
        {["Training set required", "Validation set required", "Human review required"].map((x) => (
          <div key={x} className="mt-3 rounded-2xl border p-3 text-sm">
            <div className="font-semibold">{x}</div>
            <div className="mt-1 text-xs text-muted-foreground">Controlled by LearningState and capability eligibility.</div>
            <button disabled className="mt-2 rounded-lg border px-3 py-1 text-xs text-primary hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">Unavailable</button>
          </div>
        ))}
        <button disabled className="mt-3 w-full rounded-xl border py-2 text-sm text-primary hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">No backend suggestions</button>
      </div>
    </aside>
  );
}

export function LearningMode() {
  const capabilities = get_capabilities();
  const fallbackSelfDecision = capabilities.self_decision.eligibility ?? DEFAULT_SELF_DECISION;
  const [selfDecision, setSelfDecision] = useState<SelfDecisionStatusDTO>(fallbackSelfDecision);

  useEffect(() => {
    let active = true;
    setSelfDecision(fallbackSelfDecision);
    get_self_decision_status()
      .then((status) => {
        if (active) {
          setSelfDecision(status);
        }
      })
      .catch(() => {
        if (active) {
          setSelfDecision(fallbackSelfDecision);
        }
      });
    return () => {
      active = false;
    };
  }, [fallbackSelfDecision.eligible, fallbackSelfDecision.reason]);

  return (
    <div className="flex flex-1 min-w-0 h-full">
      <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
        <div className="flex items-center justify-between border-b bg-card/80 px-5 py-4 backdrop-blur md:px-8">
          <div>
            <div className="flex items-center gap-2 text-lg font-bold">
              <Archive className="text-primary" size={20} /> Learning mode
            </div>
            <p className="hidden sm:block text-sm text-muted-foreground">
              Configure controlled learning state, glossary review and correction gates
            </p>
          </div>
          <div className="hidden gap-2 sm:flex">
            <button disabled title="Mode selection is controlled by the Windows backend workbench." className="rounded-2xl border bg-muted px-4 py-2 text-sm hover:bg-muted/80 transition disabled:cursor-not-allowed disabled:opacity-50">
              <FolderUp size={16} className="mr-2 inline" />
              Local mode
            </button>
            <button disabled title="Mode selection is controlled by the Windows backend workbench." className="rounded-2xl border border-primary bg-card px-4 py-2 text-sm text-primary shadow-sm hover:bg-secondary transition disabled:cursor-not-allowed disabled:opacity-50">
              <Sparkles size={16} className="mr-2 inline" />
              AI collaboration
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 md:p-8">
          <section className="mx-auto max-w-[820px] space-y-5">
            <div className="grid gap-3 rounded-3xl border bg-card p-4 shadow-sm sm:grid-cols-3">
              <button className="rounded-2xl border border-primary bg-secondary px-4 py-3 text-sm font-semibold text-primary transition">
                Human review mode
              </button>
            <button disabled={!capabilities.self_iterative.enabled} className="rounded-2xl border px-4 py-3 text-sm text-muted-foreground hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                Custom iteration
              </button>
              <button disabled={!selfDecision.eligible} title={selfDecision.reason} className="rounded-2xl border px-4 py-3 text-sm text-muted-foreground hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                Autonomous strategy <Info size={15} className="ml-1 inline" />
              </button>
            </div>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Info size={16} /> “Autonomous strategy” is available after AI collaboration learns enough verified examples.
            </p>

            <LearningMessage
              title="Step 1: Upload training set"
              subtitle="Training examples teach the model your preferred terminology and writing style."
              file="Not selected"
              size="Desktop file picker required"
              status="Waiting"
              meta="training_set"
              time="-"
            />
            <LearningMessage
              title="Step 2: Upload validation set"
              subtitle="Validation examples check model quality before applying the learned rules."
              file="Not selected"
              size="Desktop file picker required"
              status="Waiting"
              meta="validation_set"
              time="-"
            />

            <div className="flex items-start gap-3">
              <BotAvatar />
              <div className="flex-1 rounded-3xl border bg-card p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-bold">Ready to start training</div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      AI will combine AI collaboration + human review to optimize future translations.
                    </p>
                  </div>
                  <button disabled title={selfDecision.reason} className="rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition disabled:cursor-not-allowed disabled:opacity-50">
                    <Play size={17} className="mr-2 inline" />
                    Start training
                  </button>
                </div>
              </div>
            </div>

            <TrainingProgress />
          </section>
        </div>
      </main>
      <LearningInsight />
    </div>
  );
}

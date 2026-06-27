import { useEffect, useState } from "react";
import { Sparkles, FileText, Image, Check, Plus, Send, ChevronDown, FolderUp } from "lucide-react";
import { BotAvatar } from "../components/Sidebar";
import { get_capabilities } from "../../contracts/capability_map";
import { map_task_status } from "../../contracts/task_status";
import {
  is_backend_bridge_available,
  translate_text,
  type TranslationResultDTO,
} from "../../contracts/backend_bridge";

const TARGET_LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ja", label: "Japanese" },
  { value: "zh", label: "Chinese" },
] as const;

function targetLanguageLabel(value: string): string {
  return TARGET_LANGUAGES.find((language) => language.value === value)?.label || value;
}

function Composer({ sourceText, setSourceText, selectedTargetLang, setSelectedTargetLang, onTranslate, bridgeReady, busy }: any) {
  return (
    <div className="rounded-3xl border bg-card p-3 shadow-sm mt-auto mb-4 mx-4 md:mx-8">
      <div className="flex items-center gap-3">
        <button
          aria-label="Add file or image"
          disabled
          title="Use the Windows workbench file/OCR entries for file and image translation."
          className="grid size-11 shrink-0 place-items-center rounded-full border border-primary/20 bg-secondary text-primary shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus size={22} />
        </button>
        <input
          value={sourceText}
          onChange={(event) => setSourceText(event.target.value)}
          className="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm outline-none"
          placeholder="Type or paste text to translate"
        />
        <span className="text-xs text-muted-foreground hidden sm:inline">{sourceText.length} / 5000</span>
        <button
          onClick={onTranslate}
          disabled={!bridgeReady || busy || !sourceText.trim()}
          className="grid size-11 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between border-t pt-3 text-sm">
        <label className="flex min-w-0 flex-1 items-center gap-2">
          <span className="shrink-0">Target language</span>
          <select
            value={selectedTargetLang}
            onChange={(event) => setSelectedTargetLang(event.target.value)}
            className="min-w-0 rounded-xl border bg-card px-2 py-1 text-sm font-semibold outline-none"
          >
            {TARGET_LANGUAGES.map((language) => (
              <option key={language.value} value={language.value}>{language.label}</option>
            ))}
          </select>
        </label>
        <ChevronDown size={18} className="shrink-0" />
      </div>
    </div>
  );
}

export function MainWorkspace() {
  const capabilities = get_capabilities();
  const [sourceText, setSourceText] = useState("");
  const [selectedTargetLang, setSelectedTargetLang] = useState("en");
  const [bridgeReady, setBridgeReady] = useState(is_backend_bridge_available());
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TranslationResultDTO | null>(null);
  const [errorText, setErrorText] = useState("");
  const taskStatus = result?.task_status ?? map_task_status(busy ? "running" : "idle");
  const inputCards = [
    { icon: FileText, name: "File translation", meta: capabilities.file_translation.reason || "Available in Windows workbench", color: "bg-blue-600", enabled: capabilities.file_translation.enabled },
    { icon: Image, name: "Image / OCR", meta: capabilities.image_translation.reason || "Partial capability; use the Windows connector/runtime path.", color: "bg-pink-500", enabled: capabilities.image_translation.enabled },
    { icon: Sparkles, name: "Typed text", meta: "256 chars", color: "bg-indigo-500", enabled: capabilities.text_translation.enabled }
  ];

  useEffect(() => {
    const markReady = () => setBridgeReady(true);
    const markUnavailable = () => setBridgeReady(false);
    window.addEventListener("consensus-bridge-ready", markReady);
    window.addEventListener("consensus-bridge-unavailable", markUnavailable);
    const timer = window.setInterval(() => {
      if (is_backend_bridge_available()) {
        setBridgeReady(true);
      }
    }, 250);
    return () => {
      window.removeEventListener("consensus-bridge-ready", markReady);
      window.removeEventListener("consensus-bridge-unavailable", markUnavailable);
      window.clearInterval(timer);
    };
  }, []);

  async function runTranslation() {
    setBusy(true);
    setErrorText("");
    setResult(null);
    try {
      const response = await translate_text({
        text: sourceText,
        source_lang: "auto",
        target_lang: selectedTargetLang,
        topic: "general",
        mode: "local",
        workflow_mode: "standard",
      });
      setResult(response);
      if (!response.ok) {
        setErrorText(response.message || response.error_code);
      }
    } catch (error: any) {
      setErrorText(error?.message || "backend contract bridge unavailable");
    } finally {
      setBusy(false);
    }
  }

  async function copyTranslation() {
    if (!result?.consensus.final_text) {
      return;
    }
    try {
      await navigator.clipboard.writeText(result.consensus.final_text);
    } catch (error: any) {
      setErrorText(error?.message || "Clipboard copy is not available in this view.");
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full" data-task-status={taskStatus}>
      <div className="flex items-center justify-between border-b bg-card/80 px-4 py-3 md:px-8 md:py-4 backdrop-blur">
        <div>
          <div className="flex items-center gap-2 text-lg font-bold">
            <Sparkles className="text-primary" size={20} />
            <span className="hidden sm:inline">Standard translation</span>
            <span className="sm:hidden">Lingua Agent</span>
          </div>
          <p className="hidden sm:block text-sm text-muted-foreground">Translate documents, images and typed text with AI-assisted terminology control</p>
        </div>
        <div className="hidden gap-2 sm:flex">
          <button disabled title={capabilities.local_mode.reason} className="rounded-2xl border bg-muted px-4 py-2 text-sm hover:bg-muted/80 transition disabled:cursor-not-allowed disabled:opacity-50">
            <FolderUp size={16} className="mr-2 inline" /> Local mode
          </button>
          <button disabled title={capabilities.ai_mode.reason} className="rounded-2xl border border-primary bg-card px-4 py-2 text-sm text-primary shadow-sm hover:bg-secondary transition disabled:cursor-not-allowed disabled:opacity-50">
            <Sparkles size={16} className="mr-2 inline" /> AI collaboration
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8 space-y-6">
        <section className="mx-auto max-w-[760px] space-y-5 pb-8">
          <div className="flex gap-4">
            <BotAvatar />
            <div>
              <h2 className="text-xl md:text-2xl font-bold tracking-[-.01em]">Translation workspace</h2>
              <p className="mt-1 max-w-lg text-sm md:text-base text-muted-foreground">
                {bridgeReady ? "Backend contract bridge connected." : "Backend contract bridge unavailable in this view."}
              </p>
            </div>
          </div>

          <div className="ml-0 md:ml-auto max-w-full md:max-w-[590px] rounded-3xl border border-primary/15 bg-gradient-to-br from-indigo-50 to-white p-4 shadow-sm">
            <div className="mb-3 font-semibold text-sm md:text-base">Translate the following content to {targetLanguageLabel(selectedTargetLang)}</div>
            <div className="grid gap-3 sm:grid-cols-3">
              {inputCards.map((f: any) => (
                <div key={f.name} aria-disabled={!f.enabled} title={!f.enabled ? f.meta : undefined} className={`rounded-2xl border bg-card p-3 shadow-sm transition ${f.enabled ? "hover:shadow-md" : "opacity-60"}`}>
                  <div className="flex items-center gap-3">
                    <div className={`grid size-9 place-items-center rounded-xl text-white ${f.color}`}>
                      <f.icon size={18} />
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{f.name}</div>
                      <div className="text-xs text-muted-foreground">{f.meta}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {busy && <div className="flex items-start gap-3">
            <BotAvatar />
            <div className="rounded-3xl border bg-card p-4 shadow-sm">
              <div className="flex items-center gap-2 font-semibold">
                <span className="size-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Translating…
              </div>
              <p className="mt-2 text-sm text-muted-foreground">Analyzing content, termbase matches and output tone.</p>
            </div>
          </div>}

          {errorText && <div className="rounded-3xl border border-red-200 bg-red-50 p-4 md:p-5 shadow-sm md:ml-[56px] text-sm text-red-700">
            {errorText}
          </div>}

          {result?.ok && <div className="rounded-3xl border bg-card p-4 md:p-5 shadow-sm md:ml-[56px]">
            <div className="flex items-center gap-2 font-bold text-sm md:text-base">
              Result ready
              <Check className="rounded-full bg-emerald-100 p-0.5 text-emerald-600" size={18} />
            </div>
            <div className="mt-4 rounded-2xl border border-primary/15 bg-indigo-50/60 p-4">
              <div className="mb-2 text-xs font-semibold text-primary">TRANSLATION · {targetLanguageLabel(selectedTargetLang)}</div>
              <p className="text-sm leading-6">{result.consensus.final_text}</p>
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={copyTranslation} disabled={!result.consensus.final_text} className="text-xs border rounded-lg px-3 py-1.5 hover:bg-muted font-medium disabled:cursor-not-allowed disabled:opacity-50">Copy</button>
              <button disabled title="Termbase writeback requires explicit review confirmation in the Windows workbench." className="text-xs border rounded-lg px-3 py-1.5 hover:bg-muted font-medium disabled:cursor-not-allowed disabled:opacity-50">Add to termbase</button>
              <button disabled data-finalize-event="rating_submit" title="Rating submission is available after review in the Windows workbench." className="text-xs border rounded-lg px-3 py-1.5 hover:bg-muted font-medium ml-auto disabled:cursor-not-allowed disabled:opacity-50">Rate: Up</button>
              <button disabled data-finalize-event="rating_submit" title="Rating submission is available after review in the Windows workbench." className="text-xs border rounded-lg px-3 py-1.5 hover:bg-muted font-medium disabled:cursor-not-allowed disabled:opacity-50">Down</button>
            </div>
          </div>}
        </section>
      </div>
      
      <div className="bg-gradient-to-t from-white via-white to-transparent pt-4">
        <Composer
          sourceText={sourceText}
          setSourceText={setSourceText}
          selectedTargetLang={selectedTargetLang}
          setSelectedTargetLang={setSelectedTargetLang}
          onTranslate={runTranslation}
          bridgeReady={bridgeReady}
          busy={busy}
        />
      </div>
    </main>
  );
}

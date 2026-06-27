import { useEffect, useState } from "react";
import { ArrowLeft, Copy, Download, RefreshCw, Star, ThumbsDown, ThumbsUp } from "lucide-react";
import { Link, useParams } from "react-router";
import { list_history, type HistoryRecordDTO } from "../../contracts/backend_bridge";

export function TranslationDetail() {
  const { id } = useParams();
  const [item, setItem] = useState<HistoryRecordDTO | null>(null);
  const [status, setStatus] = useState("Loading translation detail...");

  async function copyText(value: string | undefined) {
    if (!value) {
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      setStatus("Copied to clipboard.");
    } catch {
      setStatus("Clipboard copy is not available in this view.");
    }
  }

  useEffect(() => {
    list_history()
      .then((records) => {
        const found = records.find((record) => record.id === id || record.run_id === id) || null;
        setItem(found);
        setStatus(found ? "" : "No matching desktop history record.");
      })
      .catch((error: any) => setStatus(error?.message || "Backend contract bridge unavailable."));
  }, [id]);

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/history" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <div className="text-lg font-bold">{item?.run_id || "Translation detail"}</div>
          <p className="text-sm text-muted-foreground">{item ? `${item.source_language} → ${item.target_language}` : status}</p>
        </div>
        <div className="ml-auto flex gap-2">
          <button disabled title="Re-translate is available from the Windows workbench." className="hidden sm:flex items-center gap-2 rounded-xl border bg-card px-3 py-1.5 text-sm hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
            <RefreshCw size={16} /> Re-translate
          </button>
          <button disabled title="Detail export is available from the Windows workbench." className="flex items-center gap-2 rounded-xl border bg-card px-3 py-1.5 text-sm hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
            <Download size={16} /> Export
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-5xl grid gap-6 md:grid-cols-2 h-full">
          {/* Source */}
          <div className="flex flex-col rounded-3xl border bg-card shadow-sm overflow-hidden">
            <div className="border-b bg-muted/30 px-5 py-3 text-sm font-semibold flex justify-between items-center">
              Source (中文)
              <button onClick={() => copyText(item?.source_text)} disabled={!item?.source_text} className="text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"><Copy size={16}/></button>
            </div>
            <div className="flex-1 p-5 overflow-auto text-sm leading-7">
              <p>{item?.source_text || status}</p>
            </div>
          </div>

          {/* Target */}
          <div className="flex flex-col rounded-3xl border border-primary/20 bg-indigo-50/30 shadow-sm overflow-hidden">
            <div className="border-b border-primary/10 bg-indigo-50/50 px-5 py-3 text-sm font-semibold text-primary flex justify-between items-center">
              Translation (English)
              <button onClick={() => copyText(item?.translated_text)} disabled={!item?.translated_text} className="text-primary hover:text-primary/80 disabled:cursor-not-allowed disabled:opacity-50"><Copy size={16}/></button>
            </div>
            <div className="flex-1 p-5 overflow-auto text-sm leading-7">
              <p>{item?.translated_text || status}</p>
            </div>
            
            {/* Feedback footer */}
            <div className="border-t border-primary/10 bg-white/50 px-5 py-3 flex items-center justify-between">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">Rate this translation:</span>
                <button disabled className="hover:text-emerald-600 transition disabled:cursor-not-allowed disabled:opacity-50"><ThumbsUp size={18}/></button>
                <button disabled className="hover:text-red-600 transition disabled:cursor-not-allowed disabled:opacity-50"><ThumbsDown size={18}/></button>
              </div>
              <button disabled className="text-sm font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50">Add to Termbase</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

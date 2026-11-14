import { useState, useRef } from 'react';
import {
  ShieldAlert,
  Cpu,
  BarChart3,
  FileText,
  CheckCircle2,
  Clock,
  ExternalLink,
  Sparkles,
  Terminal,
  Activity,
  Layers
} from 'lucide-react';

interface CitationItem {
  claim: string;
  source_id: string;
  source_type: string;
  source_url?: string;
}

interface ReportData {
  run_id: string;
  markdown: string;
  citations: CitationItem[];
  disclaimer: string;
}

interface ArtifactItem {
  kind: string;
  path: string;
  caption: string;
}

interface AgentMessage {
  agent: string;
  role: string;
  content: string;
  tool_calls?: any;
  created_at: string;
}

const PRESET_QUERIES = [
  { ticker: 'AAPL', q: 'How has Apple performed over the past year and what are the key risks disclosed in 10-K filings?' },
  { ticker: 'NVDA', q: 'Analyze NVIDIA valuation multiples, volatility profile, and semiconductor supply chain risks.' },
  { ticker: 'TSLA', q: 'Evaluate Tesla annual price performance, moving average signals, and regulatory headwinds.' },
  { ticker: 'MSFT', q: 'Review Microsoft cloud revenue growth, P/E ratio, and operational risk factors.' },
];

const AGENT_STAGES = [
  { id: 'planner', name: 'Planner Agent', desc: 'Query decomposition' },
  { id: 'data_agent', name: 'Data Agent', desc: 'SEC EDGAR & Market ingestion' },
  { id: 'analyst_agent', name: 'Analyst Agent', desc: 'Sandboxed Python calculations & charts' },
  { id: 'rag_agent', name: 'RAG Agent', desc: 'Qualitative vector retrieval' },
  { id: 'writer_agent', name: 'Writer Agent', desc: 'Evidence-backed brief synthesis' },
  { id: 'critic_agent', name: 'Critic Verifier', desc: 'Deterministic citation audit' },
];

export default function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [question, setQuestion] = useState(PRESET_QUERIES[0].q);
  const [isRunning, setIsRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<string>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [traceLogs, setTraceLogs] = useState<AgentMessage[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);
  const [activeTab, setActiveTab] = useState<'report' | 'charts' | 'trace'>('report');

  const wsRef = useRef<WebSocket | null>(null);

  const startResearch = async (targetTicker: string = ticker, targetQuestion: string = question) => {
    setIsRunning(true);
    setReport(null);
    setArtifacts([]);
    setTraceLogs([]);
    setActiveStage('planner');

    try {
      const resp = await fetch('/api/v1/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: targetTicker, question: targetQuestion })
      });
      const data = await resp.json();
      const runId = data.id;
      setActiveRunId(runId);

      // Connect WebSocket for live step streaming
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/runs/${runId}/stream`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.node) {
            setActiveStage(payload.node);
          }
        } catch (e) {
          console.error(e);
        }
      };

      // Poll until completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResp = await fetch(`/api/v1/runs/${runId}`);
          const statusData = await statusResp.json();

          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(pollInterval);
            setIsRunning(false);
            setActiveStage('completed');
            if (wsRef.current) wsRef.current.close();

            // Fetch final report, artifacts, and full trace
            const [reportResp, artResp, traceResp] = await Promise.all([
              fetch(`/api/v1/runs/${runId}/report`),
              fetch(`/api/v1/runs/${runId}/artifacts`),
              fetch(`/api/v1/runs/${runId}/trace`)
            ]);

            if (reportResp.ok) setReport(await reportResp.json());
            if (artResp.ok) setArtifacts(await artResp.json());
            if (traceResp.ok) setTraceLogs(await traceResp.json());
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 1500);

    } catch (err) {
      console.error('Failed to dispatch research:', err);
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-[#0d1322]/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-blue-600/20 p-2 rounded-lg border border-blue-500/30">
            <Cpu className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg text-slate-100 tracking-tight">Autonomous Research Analyst</h1>
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-950 text-blue-300 border border-blue-800 rounded-full">
                LangGraph Multi-Agent
              </span>
            </div>
            <p className="text-xs text-slate-400">Verifiable citations • Subprocess sandbox • Deterministic verification</p>
          </div>
        </div>

        {/* System Badges */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>API Online</span>
          </div>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 text-slate-400 border border-slate-800">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>SEC EDGAR & yfinance Live</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Research Input Card */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Equity Ticker
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="e.g. AAPL"
                  className="w-full bg-[#0b0f19] border border-slate-700 rounded-lg px-3.5 py-2.5 text-slate-100 font-mono font-bold focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="md:col-span-3">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Research Question
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Enter custom research query..."
                  className="w-full bg-[#0b0f19] border border-slate-700 rounded-lg pl-3.5 pr-28 py-2.5 text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm"
                />
                <button
                  onClick={() => startResearch()}
                  disabled={isRunning}
                  className="absolute right-1.5 top-1.5 bottom-1.5 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-md font-medium text-xs flex items-center space-x-1.5 transition-colors"
                >
                  {isRunning ? (
                    <>
                      <Activity className="w-3.5 h-3.5 animate-spin" />
                      <span>Synthesizing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Run Analysis</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="flex items-center space-x-2 pt-1 overflow-x-auto text-xs text-slate-400">
            <span className="font-semibold text-slate-500 flex items-center space-x-1">
              <span>Presets:</span>
            </span>
            {PRESET_QUERIES.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setTicker(p.ticker);
                  setQuestion(p.q);
                  startResearch(p.ticker, p.q);
                }}
                disabled={isRunning}
                className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors whitespace-nowrap"
              >
                <strong className="text-blue-400">{p.ticker}</strong>: {p.q.slice(0, 42)}...
              </button>
            ))}
          </div>
        </div>

        {/* Live Multi-Agent Workflow Stepper */}
        <div className="bg-[#111827] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              <span>Multi-Agent State Graph</span>
            </span>
            {activeRunId && (
              <span className="font-mono text-slate-500">Run ID: {activeRunId}</span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-2.5">
            {AGENT_STAGES.map((st) => {
              const isActive = activeStage === st.id;
              const isPast = activeStage === 'completed' || (!isRunning && report !== null);

              return (
                <div
                  key={st.id}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    isActive
                      ? 'bg-blue-950/40 border-blue-500 text-blue-200 ring-1 ring-blue-500/50'
                      : isPast
                      ? 'bg-slate-900/60 border-slate-800 text-slate-400'
                      : 'bg-slate-950/40 border-slate-900 text-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold">{st.name}</span>
                    {isActive ? (
                      <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
                    ) : isPast ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Clock className="w-3.5 h-3.5 text-slate-700" />
                    )}
                  </div>
                  <p className="text-[11px] leading-tight line-clamp-2 opacity-80">{st.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Dashboard Tabs */}
        <div className="flex border-b border-slate-800 space-x-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab('report')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'report'
                ? 'border-blue-500 text-blue-400 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Research Brief</span>
          </button>

          <button
            onClick={() => setActiveTab('charts')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'charts'
                ? 'border-blue-500 text-blue-400 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Visual Artifacts ({artifacts.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('trace')}
            className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
              activeTab === 'trace'
                ? 'border-blue-500 text-blue-400 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Agent Traces ({traceLogs.length})</span>
          </button>
        </div>

        {/* Tab 1: Research Brief */}
        {activeTab === 'report' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              {report ? (
                <div className="bg-[#111827] border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
                  <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                    {report.markdown}
                  </div>
                </div>
              ) : (
                <div className="bg-[#111827] border border-slate-800 rounded-xl p-12 text-center text-slate-500">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p className="text-base font-medium text-slate-400">No research brief generated yet.</p>
                  <p className="text-xs text-slate-500 mt-1">Select a preset or enter a ticker above and click "Run Analysis".</p>
                </div>
              )}
            </div>

            {/* Citations Inspector Sidebar */}
            <div className="space-y-4">
              <div className="bg-[#111827] border border-slate-800 rounded-xl p-4 shadow-xl">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Verified Citations ({report?.citations.length || 0})</span>
                </h3>

                {report && report.citations.length > 0 ? (
                  <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                    {report.citations.map((c, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedCitation(c)}
                        className={`p-3 rounded-lg border text-xs cursor-pointer transition-colors ${
                          selectedCitation?.source_id === c.source_id
                            ? 'bg-blue-950/40 border-blue-500 text-blue-200'
                            : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono font-bold text-[11px] text-blue-400">
                            [{c.source_id}]
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold bg-slate-800 text-slate-400">
                            {c.source_type}
                          </span>
                        </div>
                        <p className="leading-tight opacity-90">{c.claim}</p>
                        {c.source_url && (
                          <a
                            href={c.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1 mt-2 text-blue-400 hover:underline text-[11px]"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span>Open source document</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">Citations will appear here after analysis completes.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Visual Artifacts Gallery */}
        {activeTab === 'charts' && (
          <div className="space-y-6">
            {artifacts.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {artifacts.map((art, idx) => (
                  <div key={idx} className="bg-[#111827] border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                    <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-300">{art.caption}</span>
                      <span className="text-[11px] font-mono text-slate-500">{art.kind}</span>
                    </div>
                    <div className="p-4 bg-[#0b0f19] flex items-center justify-center">
                      <img
                        src={`/${art.path}`}
                        alt={art.caption}
                        className="rounded-lg max-h-[380px] w-auto object-contain border border-slate-800 shadow-md hover:scale-[1.01] transition-transform"
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-[#111827] border border-slate-800 rounded-xl p-12 text-center text-slate-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-base font-medium text-slate-400">No chart artifacts available.</p>
                <p className="text-xs text-slate-500 mt-1">The Analyst agent generates price and volatility charts during each run.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Chronological Agent Trace Audit */}
        {activeTab === 'trace' && (
          <div className="bg-[#111827] border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Terminal className="w-4 h-4 text-blue-400" />
              <span>Full Agent Execution Trace Log</span>
            </h3>

            {traceLogs.length > 0 ? (
              <div className="space-y-3 font-mono text-xs">
                {traceLogs.map((msg, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-[#0b0f19] border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="font-bold text-blue-400">@{msg.agent}</span>
                      <span className="text-[10px] text-slate-600">{new Date(msg.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-slate-300 whitespace-pre-wrap">{msg.content}</p>
                    {msg.tool_calls && (
                      <div className="bg-slate-900/80 p-2 rounded text-[11px] text-slate-400 border border-slate-800/80">
                        <span className="text-slate-500 font-semibold block mb-1">Payload:</span>
                        <pre className="text-slate-300 overflow-x-auto">{JSON.stringify(msg.tool_calls, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 text-xs">
                No trace logs available.
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-4 text-center text-xs text-slate-500 mt-auto">
        Autonomous Multi-Agent Equity Research Analyst • Powered by LangGraph & Gemini
      </footer>
    </div>
  );
}

import React, { useState, useRef, useEffect, useLayoutEffect } from "react";
import {
  Compass, Search, Milestone, Award, PlayCircle, CheckCircle2, Circle,
  Flag, User, X, ExternalLink, ArrowRight, MapPin, LogOut, ShieldCheck,
} from "lucide-react";

// ---------------------------------------------------------------------------
// This site now talks to the real SkillPath backend (Flask + database) —
// skills, roadmaps, progress, and bookmarks all come from the API below
// instead of hardcoded data. Run the backend first: `python app.py`
// (see skillpath-backend/README.txt). If it's not running, the site still
// loads but shows a connection error instead of roadmap content.
// ---------------------------------------------------------------------------
// The server address follows the address you opened the site at (localhost or 127.0.0.1).
// They must match: if the page is on "localhost" but the API is on "127.0.0.1", the browser
// treats them as different sites and silently drops the login cookie (every save then fails).
const API_BASE = `http://${window.location.hostname || "127.0.0.1"}:5000/api`;

// Search-only synonyms — the actual roadmap content lives in the backend.
const ALIASES = {
  python: ["python", "py"],
  datascience: ["data science", "ds", "data analytics", "machine learning", "ml"],
  aws: ["aws", "cloud", "cloud computing", "amazon web services"],
  webdev: ["web development", "web dev", "html", "css", "javascript", "js", "react", "frontend"],
  cyber: ["cybersecurity", "cyber security", "security", "ethical hacking"],
};

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}
const PROVIDERS = [
  { name: "IBM SkillsBuild", note: "Free courses & badges across tech and workplace skills.", url: "https://skillsbuild.org" },
  { name: "Grow with Google", note: "Free certificates in data, IT support, UX, and more.", url: "https://grow.google/certificates/" },
  { name: "AWS Skill Builder", note: "Free, self-paced cloud training straight from AWS.", url: "https://skillbuilder.aws" },
  { name: "Cisco Networking Academy", note: "Free networking & cybersecurity courses.", url: "https://www.netacad.com" },
  { name: "freeCodeCamp", note: "Free certifications in web dev, data, and more.", url: "https://www.freecodecamp.org" },
  { name: "Kaggle Learn", note: "Short, free, hands-on data & ML micro-courses.", url: "https://www.kaggle.com/learn" },
  { name: "HP LIFE", note: "Free business & tech skills courses.", url: "https://www.life-global.org" },
];

const HOW_IT_WORKS = [
  { icon: Search, title: "Search a skill", text: "Type in what you want to learn — Python, AWS, Web Dev, anything." },
  { icon: Milestone, title: "Get a roadmap", text: "SkillPath lays out a structured, step-by-step path for that skill." },
  { icon: PlayCircle, title: "Learn for free", text: "Every step links to a free video playlist and a free certification." },
  { icon: CheckCircle2, title: "Track your progress", text: "Mark steps as reached and bookmark resources to come back to." },
];

// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// roadmap.sh-style roadmap graph, and the separate Videos tab.
// ---------------------------------------------------------------------------
function youtubeId(url) {
  const m = /[?&]v=([^&]+)/.exec(url || "");
  return m ? m[1] : null;
}

function MainNode({ m, done, marked, onClick, innerRef }) {
  return (
    <button ref={innerRef} onClick={onClick} className={`rs-main ${done ? "is-done" : ""}`}>
      <span className="t">
        {done && <CheckCircle2 size={16} />}
        <span>{m.title}</span>
        {marked && <Flag size={13} fill="#111" />}
      </span>
      <span className="d">{m.duration}</span>
    </button>
  );
}

function SubNode({ s, covered, onClick, innerRef }) {
  return (
    <button ref={innerRef} onClick={onClick} className={`rs-sub ${covered ? "is-covered" : ""}`}>
      {s.title}
    </button>
  );
}

function RoadmapGraph({ skill, completed, bookmarked, onPickModule, onPickSub }) {
  const wrapRef = useRef(null);
  const nodeRefs = useRef({});
  const [paths, setPaths] = useState([]);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 760px)");
    const handler = () => setNarrow(mq.matches);
    handler();
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Measure the boxes and draw the connecting lines (solid spine + curved dashed branches).
  useLayoutEffect(() => {
    if (narrow) { setPaths([]); return undefined; }
    const compute = () => {
      const wrap = wrapRef.current;
      if (!wrap) return;
      const wr = wrap.getBoundingClientRect();
      const rel = (el) => {
        const r = el.getBoundingClientRect();
        return {
          l: r.left - wr.left, r: r.right - wr.left, t: r.top - wr.top, b: r.bottom - wr.top,
          cx: (r.left + r.right) / 2 - wr.left, cy: (r.top + r.bottom) / 2 - wr.top,
        };
      };
      const out = [];
      const titleEl = nodeRefs.current.title;
      let prev = titleEl ? rel(titleEl) : null;
      skill.modules.forEach((m) => {
        const mainEl = nodeRefs.current[`m${m.id}`];
        if (!mainEl) return;
        const mr = rel(mainEl);
        if (prev) out.push({ d: `M${prev.cx},${prev.b} L${mr.cx},${mr.t}`, dashed: false });
        prev = mr;
        (m.subtopics || []).forEach((s, i) => {
          const el = nodeRefs.current[`s${s.id}`];
          if (!el) return;
          const sr = rel(el);
          const left = i % 2 === 0;
          const sx = left ? mr.l : mr.r;
          const ex = left ? sr.r : sr.l;
          const dx = Math.abs(ex - sx) * 0.55;
          out.push({
            d: `M${sx},${mr.cy} C${left ? sx - dx : sx + dx},${mr.cy} ${left ? ex + dx : ex - dx},${sr.cy} ${ex},${sr.cy}`,
            dashed: true,
          });
        });
      });
      setPaths(out);
    };
    compute();
    const ro = new ResizeObserver(compute);
    ro.observe(wrapRef.current);
    window.addEventListener("resize", compute);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(compute);
    return () => { ro.disconnect(); window.removeEventListener("resize", compute); };
  }, [skill, narrow, completed, bookmarked]);

  const setRef = (key) => (el) => { nodeRefs.current[key] = el; };

  if (narrow) {
    return (
      <div className="rs-canvas">
        <div className="rs-title">{skill.name}</div>
        {skill.modules.map((m) => (
          <div key={m.id} style={{ marginTop: 24 }}>
            <MainNode m={m} done={!!completed[m.id]} marked={!!bookmarked[m.id]} onClick={() => onPickModule(m)} />
            <div className="rs-narrow-subs">
              {(m.subtopics || []).map((s) => (
                <SubNode key={s.id} s={s} covered={!!completed[m.id]} onClick={() => onPickSub(m, s)} />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="rs-canvas">
      <div className="rs-wrap" ref={wrapRef}>
        <svg className="rs-svg" aria-hidden="true">
          {paths.map((p, i) => (
            <path
              key={i} d={p.d} fill="none" stroke="#111"
              strokeWidth={p.dashed ? 1.6 : 2.4}
              strokeDasharray={p.dashed ? "6 5" : undefined}
            />
          ))}
        </svg>

        <div className="rs-title" ref={setRef("title")}>{skill.name}</div>

        {skill.modules.map((m) => {
          const subs = m.subtopics || [];
          const left = subs.filter((_, i) => i % 2 === 0);
          const right = subs.filter((_, i) => i % 2 === 1);
          const covered = !!completed[m.id];
          return (
            <div key={m.id} className="rs-row">
              <div className="rs-col left">
                {left.map((s) => (
                  <SubNode key={s.id} s={s} covered={covered} innerRef={setRef(`s${s.id}`)} onClick={() => onPickSub(m, s)} />
                ))}
              </div>
              <MainNode
                m={m} done={covered} marked={!!bookmarked[m.id]}
                innerRef={setRef(`m${m.id}`)} onClick={() => onPickModule(m)}
              />
              <div className="rs-col right">
                {right.map((s) => (
                  <SubNode key={s.id} s={s} covered={covered} innerRef={setRef(`s${s.id}`)} onClick={() => onPickSub(m, s)} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function VideosView({ skill, focusId, onPickModule }) {
  const byUrl = new Map();
  skill.modules.forEach((m) => {
    if (!m.videoUrl) return;
    const entry = byUrl.get(m.videoUrl) || { url: m.videoUrl, title: m.videoTitle, channel: m.videoChannel, covers: [] };
    entry.covers.push(m);
    byUrl.set(m.videoUrl, entry);
  });
  const videos = [...byUrl.values()].sort((a, b) => {
    const fa = a.covers.some((m) => m.id === focusId) ? 0 : 1;
    const fb = b.covers.some((m) => m.id === focusId) ? 0 : 1;
    return fa - fb;
  });

  return (
    <div>
      <p style={{ fontSize: 13.5, opacity: 0.7, marginBottom: 18, maxWidth: 620 }}>
        Free {skill.name} videos, in one place. They open on YouTube in a new tab. Each card shows which roadmap steps it helps with.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {videos.map((v) => {
          const id = youtubeId(v.url);
          const forThisStep = v.covers.some((m) => m.id === focusId);
          return (
            <div key={v.url} className="sp-card" style={{ borderRadius: 14, overflow: "hidden", borderColor: forThisStep ? "var(--teal)" : undefined, borderWidth: forThisStep ? 2 : undefined }}>
              <a
                href={v.url} target="_blank" rel="noopener noreferrer"
                aria-label={`Watch ${v.title} on YouTube`}
                style={{ display: "block", position: "relative", background: "#12241C", minHeight: 120 }}
              >
                {id && (
                  <img
                    src={`https://img.youtube.com/vi/${id}/hqdefault.jpg`} alt="" loading="lazy"
                    style={{ width: "100%", aspectRatio: "16 / 9", objectFit: "cover", display: "block" }}
                    onError={(e) => { e.currentTarget.style.display = "none"; }}
                  />
                )}
                <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <PlayCircle size={46} color="#fff" style={{ filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.55))" }} />
                </span>
              </a>
              <div style={{ padding: 16 }}>
                {forThisStep && <p className="sp-mono sp-text-teal" style={{ fontSize: 10.5, marginBottom: 6 }}>FOR THE STEP YOU OPENED</p>}
                <h3 className="sp-display" style={{ fontSize: 16.5, fontWeight: 600, lineHeight: 1.3 }}>{v.title}</h3>
                <p style={{ fontSize: 12.5, opacity: 0.65, marginTop: 4 }}>{v.channel}</p>
                <p className="sp-mono" style={{ fontSize: 10.5, opacity: 0.55, margin: "14px 0 6px" }}>COVERS</p>
                <div className="flex flex-wrap" style={{ gap: 6 }}>
                  {v.covers.map((m) => (
                    <button
                      key={m.id} onClick={() => onPickModule(m)} className="sp-link-btn"
                      style={{ borderRadius: 999, padding: "4px 10px", fontSize: 12, cursor: "pointer", background: "transparent" }}
                      title="Open this roadmap step"
                    >
                      {m.duration} · {m.title}
                    </button>
                  ))}
                </div>
                <a
                  href={v.url} target="_blank" rel="noopener noreferrer"
                  className="sp-link-btn flex items-center gap-1.5"
                  style={{ borderRadius: 10, padding: "9px 14px", fontSize: 13.5, textDecoration: "none", marginTop: 16, justifyContent: "center" }}
                >
                  <PlayCircle size={15} /> Watch on YouTube <ExternalLink size={12} style={{ opacity: 0.5 }} />
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

async function fetchUserData() {
  const [results, certificates, bookmarkIds] = await Promise.all([
    apiFetch("/results"), apiFetch("/certificates"), apiFetch("/bookmarks"),
  ]);
  return { results, certificates, bookmarkIds };
}

// ---------------------------------------------------------------------------
// Assessment (10 questions per step), certificate, and the progress section.
// ---------------------------------------------------------------------------
const LETTERS = ["A", "B", "C", "D", "E", "F"];

function formatDate(iso) {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

function AssessmentModal({ st, onClose, setAnswer, goTo, submit, retake, openCertificate }) {
  const dialogRef = useRef(null);
  const escapedRef = useRef(false);
  const { module, loading, error, data, answers, current, submitting, result } = st;
  const qs = data ? data.questions : [];
  const q = qs[current];

  const isAnswered = (x) => {
    const a = answers[x.id];
    if (x.kind === "mcq") return typeof a === "number";
    return typeof a === "string" && a.trim() !== "" && a.trim() !== (x.starter || "").trim();
  };
  const answeredCount = qs.filter(isAnswered).length;

  useEffect(() => {
    if (dialogRef.current) dialogRef.current.scrollTop = 0;
  }, [current, !!result]);

  const requestClose = () => {
    if (!result && answeredCount > 0 && !window.confirm("Leave this assessment? Your answers will be lost.")) return;
    onClose();
  };

  const onCodeKey = (e) => {
    if (e.key === "Escape") { escapedRef.current = true; return; }
    if (e.key === "Tab" && !e.shiftKey) {
      if (escapedRef.current) { escapedRef.current = false; return; }
      e.preventDefault();
      const t = e.target;
      const s = t.selectionStart;
      setAnswer(q.id, t.value.slice(0, s) + "    " + t.value.slice(t.selectionEnd));
      requestAnimationFrame(() => { t.selectionStart = t.selectionEnd = s + 4; });
    } else {
      escapedRef.current = false;
    }
  };

  const optionText = (question, index) => (typeof index === "number" ? question.options[index] : null);

  return (
    <div className="as-overlay" role="dialog" aria-modal="true" aria-label="Step assessment">
      <div className="as-dialog sp-fade-in" ref={dialogRef}>
        <div className="flex items-start justify-between" style={{ gap: 12 }}>
          <div>
            <p className="sp-mono sp-text-teal" style={{ fontSize: 11.5 }}>
              STEP ASSESSMENT{data ? ` · ${data.module.skill.toUpperCase()}` : ""}
            </p>
            <h3 className="sp-display" style={{ fontSize: 24, fontWeight: 600, marginTop: 4 }}>{module.title}</h3>
          </div>
          <button onClick={requestClose} className="sp-icon-btn" style={{ border: "none", background: "transparent", cursor: "pointer" }} aria-label="Close assessment">
            <X size={20} />
          </button>
        </div>

        {loading && <p style={{ marginTop: 28, opacity: 0.7 }}>Loading your questions…</p>}

        {!loading && error && !data && (
          <div style={{ marginTop: 24 }}>
            <p style={{ color: "#B5483A", fontSize: 14.5 }}>{error}</p>
            <button onClick={onClose} className="sp-link-btn" style={{ marginTop: 16, borderRadius: 10, padding: "9px 16px", cursor: "pointer", background: "transparent" }}>Close</button>
          </div>
        )}

        {/* ------------------------------ QUESTIONS ------------------------------ */}
        {data && !result && q && (
          <>
            <p style={{ fontSize: 13, opacity: 0.7, marginTop: 8 }}>
              {data.total} questions · you need {data.pass_mark} correct to pass · you can retake it as many times as you like
            </p>

            <div className="flex flex-wrap" style={{ gap: 6, margin: "18px 0 22px" }} aria-label="Question navigator">
              {qs.map((x, i) => (
                <button
                  key={x.id}
                  onClick={() => goTo(i)}
                  className={`as-dot ${i === current ? "is-current" : isAnswered(x) ? "is-answered" : ""}`}
                  aria-label={`Question ${i + 1}${isAnswered(x) ? ", answered" : ""}`}
                  aria-current={i === current ? "step" : undefined}
                >
                  {i + 1}
                </button>
              ))}
            </div>

            <p className="sp-mono" style={{ fontSize: 11, opacity: 0.55 }}>
              QUESTION {current + 1} OF {qs.length}{q.kind === "code" ? " · SMALL PROGRAM" : ""}
            </p>
            <h4 className="sp-display" style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.4, margin: "8px 0 18px" }}>{q.text}</h4>

            {q.kind === "mcq" ? (
              <div className="flex flex-col" style={{ gap: 10 }} role="radiogroup" aria-label="Answer options">
                {q.options.map((opt, i) => (
                  <button
                    key={i}
                    role="radio"
                    aria-checked={answers[q.id] === i}
                    onClick={() => setAnswer(q.id, i)}
                    className={`as-opt ${answers[q.id] === i ? "is-picked" : ""}`}
                  >
                    <span className="ltr">{LETTERS[i]}</span>
                    <span>{opt}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div>
                <div className="flex items-center" style={{ gap: 8, marginBottom: 10 }}>
                  <span className="sp-mono" style={{ fontSize: 11, padding: "3px 9px", borderRadius: 999, background: "var(--forest)", color: "#F4F1E4" }}>
                    {q.language.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 12.5, opacity: 0.65 }}>Nothing is run — your answer is checked against the requirements below.</span>
                </div>
                <p className="sp-mono" style={{ fontSize: 11, opacity: 0.55, marginBottom: 6 }}>YOUR ANSWER SHOULD</p>
                <ul style={{ margin: "0 0 14px 18px", fontSize: 14, lineHeight: 1.7, listStyle: "disc" }}>
                  {q.requirements.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
                <textarea
                  className="as-code"
                  value={answers[q.id] ?? ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  onKeyDown={onCodeKey}
                  spellCheck={false}
                  autoCapitalize="off"
                  autoCorrect="off"
                  aria-label="Your code answer"
                />
                <p style={{ fontSize: 11.5, opacity: 0.55, marginTop: 6 }}>Tab inserts spaces. Press Esc, then Tab, to move on to the next control.</p>
              </div>
            )}

            <div className="flex items-center justify-between flex-wrap" style={{ gap: 10, marginTop: 26, paddingTop: 18, borderTop: "1px solid var(--line)" }}>
              <span style={{ fontSize: 13, opacity: 0.65 }}>{answeredCount} of {qs.length} answered</span>
              <div className="flex items-center" style={{ gap: 10 }}>
                <button
                  onClick={() => goTo(current - 1)}
                  disabled={current === 0}
                  className="sp-link-btn"
                  style={{ borderRadius: 10, padding: "9px 18px", cursor: current === 0 ? "default" : "pointer", background: "transparent", opacity: current === 0 ? 0.4 : 1 }}
                >
                  Back
                </button>
                {current < qs.length - 1 ? (
                  <button onClick={() => goTo(current + 1)} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "9px 22px", fontWeight: 600, cursor: "pointer" }}>
                    Next
                  </button>
                ) : (
                  <button onClick={submit} disabled={submitting} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "9px 22px", fontWeight: 600, cursor: "pointer", opacity: submitting ? 0.6 : 1 }}>
                    {submitting ? "Checking…" : "Submit answers"}
                  </button>
                )}
              </div>
            </div>
            {answeredCount < qs.length && current === qs.length - 1 && (
              <p style={{ fontSize: 12.5, color: "#9A6A12", marginTop: 10 }}>
                {qs.length - answeredCount} question{qs.length - answeredCount === 1 ? " is" : "s are"} still unanswered — they will count as wrong.
              </p>
            )}
            {error && <p style={{ color: "#B5483A", fontSize: 13, marginTop: 10 }}>{error}</p>}
          </>
        )}

        {/* ------------------------------ RESULT ------------------------------ */}
        {data && result && (
          <div>
            <div
              style={{
                margin: "22px 0", padding: "20px 22px", borderRadius: 14,
                background: result.passed ? "rgba(47,143,91,0.1)" : "rgba(181,72,58,0.08)",
                border: `1.5px solid ${result.passed ? "#2F8F5B" : "#B5483A"}`,
              }}
            >
              <div className="flex items-center flex-wrap" style={{ gap: 18 }}>
                <div className="sp-display" style={{ fontSize: 46, fontWeight: 700, lineHeight: 1 }}>
                  {result.score}<span style={{ fontSize: 24, opacity: 0.55 }}> / {result.total}</span>
                </div>
                <div>
                  <p style={{ fontWeight: 700, fontSize: 18 }}>
                    {result.passed ? "Passed — step reached!" : "Not quite yet"}
                  </p>
                  <p style={{ fontSize: 13.5, opacity: 0.8, marginTop: 2 }}>
                    {result.passed
                      ? "This step is now marked as reached on your roadmap."
                      : `You need ${result.pass_mark} to pass. Read the explanations below, then try again.`}
                  </p>
                </div>
              </div>
            </div>

            {result.certificate && (
              <div className="flex items-center justify-between flex-wrap" style={{ gap: 12, padding: "16px 20px", borderRadius: 14, background: "var(--forest)", color: "#F4F1E4", marginBottom: 22 }}>
                <div className="flex items-center" style={{ gap: 12 }}>
                  <Award size={28} style={{ color: "var(--blaze)", flexShrink: 0 }} />
                  <div>
                    <p style={{ fontWeight: 700 }}>
                      {result.certificate_is_new ? "Certificate unlocked!" : "Your certificate"}
                    </p>
                    <p style={{ fontSize: 13, opacity: 0.8 }}>
                      {result.certificate_is_new
                        ? `You have completed every step of ${result.certificate.skillName}.`
                        : `You already earned the ${result.certificate.skillName} certificate.`}
                    </p>
                  </div>
                </div>
                <button onClick={() => openCertificate(result.certificate)} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "9px 18px", fontWeight: 600, cursor: "pointer" }}>
                  View certificate
                </button>
              </div>
            )}

            <div className="flex flex-wrap" style={{ gap: 10, marginBottom: 26 }}>
              <button onClick={retake} className="sp-link-btn" style={{ borderRadius: 10, padding: "9px 18px", cursor: "pointer", background: "transparent" }}>
                {result.passed ? "Retake to improve your score" : "Retake assessment"}
              </button>
              <button onClick={onClose} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "9px 22px", fontWeight: 600, cursor: "pointer" }}>
                Back to roadmap
              </button>
            </div>

            <p className="sp-mono" style={{ fontSize: 11, opacity: 0.55, marginBottom: 10 }}>REVIEW YOUR ANSWERS</p>
            <div className="flex flex-col" style={{ gap: 14 }}>
              {qs.map((x, i) => {
                const r = result.results.find((rr) => rr.id === x.id);
                if (!r) return null;
                return (
                  <div key={x.id} style={{ border: `1.5px solid ${r.correct ? "#2F8F5B" : "#B5483A"}`, borderRadius: 12, padding: "14px 16px", background: "#fff" }}>
                    <div className="flex items-start" style={{ gap: 10 }}>
                      {r.correct
                        ? <CheckCircle2 size={19} style={{ color: "#2F8F5B", flexShrink: 0, marginTop: 2 }} />
                        : <X size={19} style={{ color: "#B5483A", flexShrink: 0, marginTop: 2 }} />}
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <p style={{ fontWeight: 600, fontSize: 14.5 }}>{i + 1}. {x.text}</p>

                        {x.kind === "mcq" ? (
                          <div style={{ fontSize: 13.5, marginTop: 8, lineHeight: 1.6 }}>
                            {!r.correct && (
                              <p>
                                <span style={{ opacity: 0.6 }}>Your answer: </span>
                                {optionText(x, r.your_index) ?? <em>skipped</em>}
                              </p>
                            )}
                            <p><span style={{ opacity: 0.6 }}>Correct answer: </span><strong>{optionText(x, r.correct_index)}</strong></p>
                          </div>
                        ) : (
                          <div style={{ fontSize: 13.5, marginTop: 8 }}>
                            <ul style={{ listStyle: "none", margin: 0, padding: 0, lineHeight: 1.8 }}>
                              {r.checks.map((c, ci) => (
                                <li key={ci} className="flex items-center" style={{ gap: 8 }}>
                                  {c.ok
                                    ? <CheckCircle2 size={15} style={{ color: "#2F8F5B", flexShrink: 0 }} />
                                    : <X size={15} style={{ color: "#B5483A", flexShrink: 0 }} />}
                                  <span>{c.label}</span>
                                </li>
                              ))}
                            </ul>
                            <p className="sp-mono" style={{ fontSize: 10.5, opacity: 0.55, margin: "12px 0 6px" }}>MODEL SOLUTION</p>
                            <pre className="as-pre">{r.solution}</pre>
                          </div>
                        )}
                        {r.explanation && (
                          <p style={{ fontSize: 13, opacity: 0.8, marginTop: 10, lineHeight: 1.55 }}>
                            <strong>Why: </strong>{r.explanation}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CertificateView({ cert, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="cert-overlay" role="dialog" aria-modal="true" aria-label={`Certificate for ${cert.skillName}`}>
      <div className="cert-toolbar no-print">
        <button onClick={() => window.print()} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "10px 20px", fontWeight: 600, cursor: "pointer" }}>
          Print / Save as PDF
        </button>
        <button onClick={onClose} className="sp-link-btn" style={{ borderRadius: 10, padding: "10px 20px", cursor: "pointer", background: "#F4F1E4" }}>
          Close
        </button>
      </div>

      <div className="cert-print">
        <div className="cert-sheet">
          <div className="cert-frame">
            <div className="cert-brand"><Compass className="cert-brand-icon" /> SkillPath</div>
            <p className="cert-kicker">CERTIFICATE OF COMPLETION</p>
            <p className="cert-small">This certifies that</p>
            <p className="cert-name">{cert.holder}</p>
            <div className="cert-rule" />
            <p className="cert-small">
              has completed all {cert.steps} steps of the roadmap and passed every assessment for
            </p>
            <p className="cert-skill">{cert.skillName}</p>
            <p className="cert-small">with an average score of <strong>{cert.averagePercent}%</strong></p>

            <div className="cert-footer">
              <div className="cert-foot-col">
                <p className="cert-foot-label">DATE OF ISSUE</p>
                <p className="cert-foot-value">{formatDate(cert.issuedAt)}</p>
              </div>
              <div className="cert-seal"><Award className="cert-seal-icon" /></div>
              <div className="cert-foot-col">
                <p className="cert-foot-label">CERTIFICATE ID</p>
                <p className="cert-foot-value cert-code">{cert.code}</p>
              </div>
            </div>
            <p className="cert-verify">Anyone can check this certificate by entering its ID in the “Verify a certificate” box on the SkillPath website.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MyProgress({ user, roadmaps, results, certificates, onSignIn, onOpenSkill, onOpenCertificate }) {
  const [code, setCode] = useState("");
  const [verdict, setVerdict] = useState(null); // null | {valid, cert} | {valid:false}
  const [checking, setChecking] = useState(false);

  async function verify(e) {
    e.preventDefault();
    const c = code.trim();
    if (!c) return;
    setChecking(true);
    try {
      const data = await apiFetch(`/certificates/verify/${encodeURIComponent(c)}`);
      setVerdict({ valid: true, cert: data });
    } catch (err) {
      setVerdict(err.status === 404 ? { valid: false } : { error: "Couldn't reach the server to check that code." });
    } finally {
      setChecking(false);
    }
  }

  const skills = Object.entries(roadmaps).map(([key, skill]) => {
    const steps = skill.modules.filter((m) => m.questionCount > 0);
    const passed = steps.filter((m) => results[m.id]?.passed);
    const percents = steps.filter((m) => results[m.id]?.total).map((m) => (results[m.id].best / results[m.id].total) * 100);
    const avg = percents.length ? Math.round(percents.reduce((a, b) => a + b, 0) / percents.length) : null;
    return { key, skill, steps, passed, avg, cert: certificates.find((c) => c.skillKey === key) };
  });
  const totalAttempts = Object.values(results).reduce((a, r) => a + r.attempts, 0);

  return (
    <section id="progress" style={{ maxWidth: 1100, margin: "0 auto", padding: "64px 20px 24px" }}>
      <p className="sp-mono sp-text-teal" style={{ fontSize: 12 }}>YOUR PROGRESS</p>
      <h2 className="sp-display" style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>Assessments &amp; certificates</h2>
      <p style={{ opacity: 0.75, fontSize: 15, marginTop: 6, maxWidth: 600 }}>
        Mark a step as reached, pass its 10-question check, and when every step of a skill is done you earn a SkillPath certificate.
      </p>

      {!user ? (
        <div className="sp-card" style={{ borderRadius: 14, padding: "22px 24px", marginTop: 26 }}>
          <p style={{ fontSize: 15 }}>Sign in to take assessments and collect certificates.</p>
          <button onClick={onSignIn} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "9px 20px", fontWeight: 600, cursor: "pointer", marginTop: 14 }}>
            Sign in
          </button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap" style={{ gap: 12, marginTop: 24 }}>
            {[
              ["Steps reached", skills.reduce((a, s) => a + s.passed.length, 0) + " / " + skills.reduce((a, s) => a + s.steps.length, 0)],
              ["Assessments taken", String(totalAttempts)],
              ["Certificates earned", String(certificates.length)],
            ].map(([label, value]) => (
              <div key={label} className="sp-card" style={{ borderRadius: 12, padding: "14px 18px", minWidth: 150 }}>
                <p className="sp-display" style={{ fontSize: 26, fontWeight: 700 }}>{value}</p>
                <p style={{ fontSize: 12.5, opacity: 0.65 }}>{label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5" style={{ marginTop: 22 }}>
            {skills.map(({ key, skill, steps, passed, avg, cert }) => {
              const pct = steps.length ? Math.round((passed.length / steps.length) * 100) : 0;
              return (
                <div key={key} className="sp-card" style={{ borderRadius: 14, padding: 20, borderColor: cert ? "var(--blaze)" : undefined }}>
                  <div className="flex items-start justify-between" style={{ gap: 8 }}>
                    <h3 className="sp-display" style={{ fontSize: 18, fontWeight: 600 }}>{skill.name}</h3>
                    {cert && <Award size={20} style={{ color: "var(--blaze)", flexShrink: 0 }} />}
                  </div>
                  <p className="sp-mono" style={{ fontSize: 11.5, opacity: 0.65, marginTop: 10 }}>
                    {passed.length} OF {steps.length} STEPS PASSED
                  </p>
                  <div className="sp-progress-track" style={{ height: 7, borderRadius: 999, overflow: "hidden", marginTop: 6 }}>
                    <div className="sp-progress-fill" style={{ height: "100%", width: `${pct}%`, borderRadius: 999 }} />
                  </div>
                  <p style={{ fontSize: 12.5, opacity: 0.7, marginTop: 8 }}>
                    {avg !== null ? `Average best score: ${avg}%` : "No assessments taken yet"}
                  </p>
                  {cert ? (
                    <button onClick={() => onOpenCertificate(cert)} className="sp-btn-blaze" style={{ width: "100%", border: "none", borderRadius: 10, padding: "9px 14px", fontWeight: 600, cursor: "pointer", marginTop: 16 }}>
                      View certificate
                    </button>
                  ) : (
                    <button onClick={() => onOpenSkill(key)} className="sp-link-btn" style={{ width: "100%", borderRadius: 10, padding: "9px 14px", cursor: "pointer", background: "transparent", marginTop: 16 }}>
                      {passed.length ? "Continue roadmap" : "Start roadmap"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      <div className="sp-card" style={{ borderRadius: 14, padding: "20px 22px", marginTop: 28 }}>
        <h3 className="sp-display" style={{ fontSize: 18, fontWeight: 600 }}>Verify a certificate</h3>
        <p style={{ fontSize: 13.5, opacity: 0.7, marginTop: 4 }}>Have a SkillPath certificate ID? Check that it is genuine.</p>
        <form onSubmit={verify} className="flex flex-wrap" style={{ gap: 10, marginTop: 14 }}>
          <input
            value={code}
            onChange={(e) => { setCode(e.target.value); setVerdict(null); }}
            placeholder="e.g. SP-PYT-0002-ABC123"
            aria-label="Certificate ID"
            className="sp-input"
            style={{ flex: "1 1 240px", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 12px", fontSize: 14, background: "var(--paper)", fontFamily: "'JetBrains Mono', monospace" }}
          />
          <button type="submit" disabled={checking} className="sp-link-btn" style={{ borderRadius: 10, padding: "9px 20px", cursor: "pointer", background: "transparent", fontWeight: 600 }}>
            {checking ? "Checking…" : "Verify"}
          </button>
        </form>
        {verdict && verdict.valid === true && (
          <p style={{ marginTop: 14, fontSize: 14.5, color: "#1F6B45" }}>
            <CheckCircle2 size={16} style={{ display: "inline", verticalAlign: -3, marginRight: 6 }} />
            <strong>Valid.</strong> Issued to <strong>{verdict.cert.holder}</strong> for <strong>{verdict.cert.skillName}</strong> on {formatDate(verdict.cert.issuedAt)} (average score {verdict.cert.averagePercent}%).
          </p>
        )}
        {verdict && verdict.valid === false && (
          <p style={{ marginTop: 14, fontSize: 14.5, color: "#B5483A" }}>
            <X size={16} style={{ display: "inline", verticalAlign: -3, marginRight: 6 }} />
            No certificate found with that ID. Check for typing mistakes.
          </p>
        )}
        {verdict && verdict.error && <p style={{ marginTop: 14, fontSize: 14, color: "#B5483A" }}>{verdict.error}</p>}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Admin console — only opened for accounts whose role is "admin".
// (The server checks the role on every call too, so hiding it here is not the security.)
// ---------------------------------------------------------------------------
const LANGUAGES = ["python", "sql", "javascript", "jsx", "html", "css", "bash", "json"];

function slugify(text) {
  return text.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
}

function AField({ label, hint, children }) {
  return (
    <label style={{ display: "block", marginBottom: 12 }}>
      <span className="ad-label">{label}</span>
      {children}
      {hint && <span className="ad-hint">{hint}</span>}
    </label>
  );
}

function AdminOverview({ say }) {
  const [st, setSt] = useState(null);
  useEffect(() => {
    let alive = true;
    apiFetch("/admin/stats").then((d) => alive && setSt(d)).catch((e) => say("err", e.message));
    return () => { alive = false; };
  }, []);
  if (!st) return <p style={{ opacity: 0.7 }}>Loading…</p>;

  const cards = [
    ["Learners", st.learners, `${st.admins} admin account${st.admins === 1 ? "" : "s"}`],
    ["Assessments taken", st.attempts, st.passRatePercent === null ? "none yet" : `${st.passRatePercent}% passed`],
    ["Certificates issued", st.certificates, "across all skills"],
    ["Content", `${st.skills} skills`, `${st.steps} steps · ${st.questions} questions`],
  ];
  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(([label, value, sub]) => (
          <div key={label} className="sp-card" style={{ borderRadius: 14, padding: "16px 18px" }}>
            <p className="sp-mono" style={{ fontSize: 10.5, opacity: 0.6 }}>{label.toUpperCase()}</p>
            <p className="sp-display" style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{value}</p>
            <p style={{ fontSize: 12.5, opacity: 0.65 }}>{sub}</p>
          </div>
        ))}
      </div>

      <h3 className="sp-display" style={{ fontSize: 20, fontWeight: 600, margin: "30px 0 12px" }}>Skills at a glance</h3>
      <div className="sp-card" style={{ borderRadius: 14, overflowX: "auto" }}>
        <table className="ad-table">
          <thead><tr><th>SKILL</th><th>STEPS</th><th>LEARNERS STARTED</th><th>CERTIFICATES</th><th>AVG BEST SCORE</th></tr></thead>
          <tbody>
            {st.perSkill.map((s) => (
              <tr key={s.key}>
                <td><strong>{s.name}</strong></td><td>{s.steps}</td><td>{s.learners}</td><td>{s.certificates}</td>
                <td>{s.averageBestPercent === null ? "—" : `${s.averageBestPercent}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="sp-display" style={{ fontSize: 20, fontWeight: 600, margin: "30px 0 12px" }}>Recent assessments</h3>
      {st.recent.length === 0 ? (
        <p style={{ opacity: 0.65, fontSize: 14 }}>Nobody has taken an assessment yet.</p>
      ) : (
        <div className="sp-card" style={{ borderRadius: 14, overflowX: "auto" }}>
          <table className="ad-table">
            <thead><tr><th>LEARNER</th><th>STEP</th><th>SCORE</th><th>RESULT</th><th>WHEN (UTC)</th></tr></thead>
            <tbody>
              {st.recent.map((r, i) => (
                <tr key={i}>
                  <td>{r.learner}</td><td>{r.step} <span style={{ opacity: 0.55 }}>· {r.skill}</span></td>
                  <td>{r.score}/{r.total}</td>
                  <td style={{ color: r.passed ? "#1F6B45" : "#B5483A", fontWeight: 600 }}>{r.passed ? "Passed" : "Not passed"}</td>
                  <td style={{ opacity: 0.7 }}>{r.when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AdminUsers({ me, say }) {
  const [users, setUsers] = useState(null);
  const [q, setQ] = useState("");
  const load = () => apiFetch("/admin/users").then(setUsers).catch((e) => say("err", e.message));
  useEffect(() => { load(); }, []);

  async function setRole(u, role) {
    try {
      await apiFetch(`/admin/users/${u.id}`, { method: "PUT", body: JSON.stringify({ role }) });
      say("ok", `${u.name} is now ${role === "admin" ? "an admin" : "a learner"}.`);
      load();
    } catch (e) { say("err", e.message); }
  }
  async function remove(u) {
    if (!window.confirm(`Delete ${u.name} (${u.email})?\n\nTheir scores, bookmarks and certificates will be deleted too. This can't be undone.`)) return;
    try {
      await apiFetch(`/admin/users/${u.id}`, { method: "DELETE" });
      say("ok", `${u.name} was deleted.`);
      load();
    } catch (e) { say("err", e.message); }
  }

  if (!users) return <p style={{ opacity: 0.7 }}>Loading…</p>;
  const shown = users.filter((u) => `${u.name} ${u.email}`.toLowerCase().includes(q.trim().toLowerCase()));
  return (
    <div>
      <div className="flex items-center justify-between flex-wrap" style={{ gap: 12, marginBottom: 14 }}>
        <p style={{ fontSize: 14, opacity: 0.7 }}>{users.length} account{users.length === 1 ? "" : "s"}</p>
        <input className="ad-input" style={{ maxWidth: 280 }} placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search users" />
      </div>
      <div className="sp-card" style={{ borderRadius: 14, overflowX: "auto" }}>
        <table className="ad-table">
          <thead><tr><th>NAME</th><th>EMAIL</th><th>ROLE</th><th>STEPS PASSED</th><th>ATTEMPTS</th><th>CERTS</th><th>JOINED</th><th /></tr></thead>
          <tbody>
            {shown.map((u) => (
              <tr key={u.id}>
                <td><strong>{u.name}</strong>{u.id === me.id && <span className="ad-badge" style={{ marginLeft: 8 }}>YOU</span>}</td>
                <td style={{ opacity: 0.8 }}>{u.email}</td>
                <td><span className={`ad-badge ${u.role === "admin" ? "is-admin" : ""}`}>{u.role === "admin" ? "ADMIN" : "LEARNER"}</span></td>
                <td>{u.stepsPassed}</td><td>{u.attempts}</td><td>{u.certificates}</td><td style={{ opacity: 0.7 }}>{u.joined}</td>
                <td style={{ whiteSpace: "nowrap", textAlign: "right" }}>
                  {u.id !== me.id && (
                    u.role === "admin"
                      ? <button className="ad-btn" onClick={() => setRole(u, "user")}>Make learner</button>
                      : <>
                          <button className="ad-btn" onClick={() => setRole(u, "admin")}>Make admin</button>{" "}
                          <button className="ad-btn danger" onClick={() => remove(u)}>Delete</button>
                        </>
                  )}
                </td>
              </tr>
            ))}
            {shown.length === 0 && <tr><td colSpan={8} style={{ opacity: 0.6 }}>No one matches that search.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TopicRow({ sub, reloadContent, say }) {
  const [d, setD] = useState({ title: sub.title, description: sub.description || "" });
  async function save() {
    try {
      await apiFetch(`/admin/subtopics/${sub.id}`, { method: "PUT", body: JSON.stringify(d) });
      await reloadContent(); say("ok", "Topic box saved.");
    } catch (e) { say("err", e.message); }
  }
  async function remove() {
    if (!window.confirm(`Delete the topic box “${sub.title}”?`)) return;
    try { await apiFetch(`/admin/subtopics/${sub.id}`, { method: "DELETE" }); await reloadContent(); say("ok", "Topic box deleted."); }
    catch (e) { say("err", e.message); }
  }
  return (
    <div className="flex flex-wrap items-center" style={{ gap: 8, marginBottom: 8 }}>
      <input className="ad-input" style={{ flex: "1 1 160px" }} value={d.title} onChange={(e) => setD({ ...d, title: e.target.value })} aria-label="Topic title" />
      <input className="ad-input" style={{ flex: "2 1 240px" }} value={d.description} onChange={(e) => setD({ ...d, description: e.target.value })} aria-label="Topic description" />
      <button className="ad-btn" onClick={save}>Save</button>
      <button className="ad-btn danger" onClick={remove}>Delete</button>
    </div>
  );
}

function QuestionForm({ initial, nextOrder, onSave, onCancel }) {
  const [kind, setKind] = useState(initial?.kind || "mcq");
  const [text, setText] = useState(initial?.text || "");
  const [explanation, setExplanation] = useState(initial?.explanation || "");
  const [options, setOptions] = useState(initial?.kind === "mcq" ? [...initial.options] : ["", "", "", ""]);
  const [correct, setCorrect] = useState(initial?.kind === "mcq" ? initial.answer_index : 0);
  const [language, setLanguage] = useState(initial?.language || "python");
  const [starter, setStarter] = useState(initial?.starter || "");
  const [solution, setSolution] = useState(initial?.solution || "");
  const [checks, setChecks] = useState(initial?.checks?.length ? initial.checks.map((c) => ({ ...c })) : [{ label: "", pattern: "" }]);
  const [err, setErr] = useState("");

  function submit(e) {
    e.preventDefault();
    setErr("");
    if (!text.trim()) return setErr("Write the question first.");
    const base = { kind, text: text.trim(), explanation: explanation.trim(), order_index: initial?.order_index ?? nextOrder };
    if (kind === "mcq") {
      const filled = options.map((o, i) => ({ o: o.trim(), i })).filter((x) => x.o);
      if (filled.length < 2) return setErr("Give at least two answer options.");
      const idx = filled.findIndex((x) => x.i === correct);
      if (idx < 0) return setErr("Pick which option is correct (and make sure it isn't empty).");
      return onSave({ ...base, options: filled.map((x) => x.o), answer_index: idx });
    }
    const cleaned = checks.map((c) => ({ label: c.label.trim(), pattern: c.pattern.trim() })).filter((c) => c.label || c.pattern);
    if (!cleaned.length || cleaned.some((c) => !c.label || !c.pattern)) return setErr("Each requirement needs both a label and a pattern.");
    for (const c of cleaned) {
      try { new RegExp(c.pattern); } catch { return setErr(`The pattern for “${c.label}” isn't a valid regular expression.`); }
    }
    const missed = cleaned.filter((c) => { try { return !new RegExp(c.pattern, "ims").test(solution); } catch { return true; } });
    if (missed.length && !window.confirm(`Your model solution doesn't satisfy: ${missed.map((c) => c.label).join(", ")}.\n\nEven a correct answer could fail those checks. Save anyway?`)) return;
    return onSave({ ...base, language, starter, solution, checks: cleaned });
  }

  return (
    <form onSubmit={submit} className="ad-form">
      <div className="flex flex-wrap" style={{ gap: 12 }}>
        <AField label="Type">
          <select className="ad-input" value={kind} onChange={(e) => setKind(e.target.value)} disabled={!!initial}>
            <option value="mcq">Multiple choice</option>
            <option value="code">Small program</option>
          </select>
        </AField>
      </div>
      <AField label="Question"><textarea className="ad-input" rows={2} value={text} onChange={(e) => setText(e.target.value)} /></AField>

      {kind === "mcq" ? (
        <AField label="Answer options" hint="Select the circle next to the correct answer. Leave unused options empty.">
          {options.map((o, i) => (
            <div key={i} className="flex items-center" style={{ gap: 8, marginBottom: 6 }}>
              <input type="radio" name="correct" checked={correct === i} onChange={() => setCorrect(i)} aria-label={`Option ${i + 1} is correct`} />
              <input className="ad-input" value={o} placeholder={`Option ${i + 1}`} onChange={(e) => setOptions(options.map((x, j) => (j === i ? e.target.value : x)))} />
            </div>
          ))}
        </AField>
      ) : (
        <>
          <div className="flex flex-wrap" style={{ gap: 12 }}>
            <AField label="Language">
              <select className="ad-input" value={language} onChange={(e) => setLanguage(e.target.value)}>
                {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </AField>
          </div>
          <AField label="Starter code (optional)"><textarea className="ad-input ad-mono" rows={3} value={starter} onChange={(e) => setStarter(e.target.value)} /></AField>
          <AField label="Model solution" hint="Shown to the learner after they submit. Your requirements below should all match it."><textarea className="ad-input ad-mono" rows={4} value={solution} onChange={(e) => setSolution(e.target.value)} /></AField>
          <AField label="Requirements" hint="The learner sees each label. The pattern is a regular expression the answer must contain (case-insensitive, comments ignored). Every requirement must match.">
            {checks.map((c, i) => (
              <div key={i} className="flex flex-wrap items-center" style={{ gap: 8, marginBottom: 6 }}>
                <input className="ad-input" style={{ flex: "1 1 200px" }} placeholder="Label, e.g. Defines a function" value={c.label} onChange={(e) => setChecks(checks.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} />
                <input className="ad-input ad-mono" style={{ flex: "1 1 200px" }} placeholder="Pattern, e.g. def\s+\w+" value={c.pattern} onChange={(e) => setChecks(checks.map((x, j) => (j === i ? { ...x, pattern: e.target.value } : x)))} />
                <button type="button" className="ad-btn danger" onClick={() => setChecks(checks.filter((_, j) => j !== i))} aria-label="Remove requirement">✕</button>
              </div>
            ))}
            <button type="button" className="ad-btn" onClick={() => setChecks([...checks, { label: "", pattern: "" }])}>+ Add requirement</button>
          </AField>
        </>
      )}

      <AField label="Explanation (shown after submitting)"><textarea className="ad-input" rows={2} value={explanation} onChange={(e) => setExplanation(e.target.value)} /></AField>
      {err && <p style={{ color: "#B5483A", fontSize: 13.5, marginBottom: 10 }}>{err}</p>}
      <div className="flex" style={{ gap: 8 }}>
        <button type="submit" className="sp-btn-blaze" style={{ border: "none", borderRadius: 8, padding: "8px 18px", fontWeight: 600, cursor: "pointer" }}>Save question</button>
        <button type="button" className="ad-btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function QuestionManager({ step, reloadContent, say }) {
  const [qs, setQs] = useState(null);
  const [editing, setEditing] = useState(null); // a question, "new", or null
  const load = () => apiFetch(`/admin/modules/${step.id}/questions`).then(setQs).catch((e) => say("err", e.message));
  useEffect(() => { load(); }, [step.id]);

  async function save(payload, id) {
    try {
      if (id) await apiFetch(`/admin/questions/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      else await apiFetch("/admin/questions", { method: "POST", body: JSON.stringify({ ...payload, module_id: step.id }) });
      say("ok", id ? "Question updated." : "Question added.");
      setEditing(null);
      await load();
      await reloadContent();
    } catch (e) { say("err", e.message); }
  }
  async function remove(q) {
    if (!window.confirm("Delete this question?")) return;
    try { await apiFetch(`/admin/questions/${q.id}`, { method: "DELETE" }); say("ok", "Question deleted."); await load(); await reloadContent(); }
    catch (e) { say("err", e.message); }
  }

  if (!qs) return <p style={{ opacity: 0.7, fontSize: 13 }}>Loading questions…</p>;
  const nextOrder = qs.length ? Math.max(...qs.map((q) => q.order_index)) + 1 : 1;
  return (
    <div>
      <p style={{ fontSize: 13, opacity: 0.7, marginBottom: 10 }}>
        {qs.length} question{qs.length === 1 ? "" : "s"} · learners need {Math.ceil(qs.length * 0.7)} correct to pass
        {qs.length === 0 && " · a step with no questions can't be marked as reached yet"}
      </p>
      {qs.map((q) => (
        editing && editing.id === q.id ? (
          <QuestionForm key={q.id} initial={q} nextOrder={nextOrder} onSave={(p) => save(p, q.id)} onCancel={() => setEditing(null)} />
        ) : (
          <div key={q.id} className="flex items-start" style={{ gap: 10, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
            <span className="sp-mono" style={{ fontSize: 11, opacity: 0.55, paddingTop: 3, minWidth: 22 }}>{q.order_index}</span>
            <span className={`ad-badge ${q.kind === "code" ? "is-admin" : ""}`} style={{ marginTop: 2 }}>{q.kind === "code" ? "CODE" : "MCQ"}</span>
            <span style={{ flex: 1, fontSize: 14, minWidth: 0 }}>{q.text}</span>
            <button className="ad-btn" onClick={() => setEditing(q)}>Edit</button>
            <button className="ad-btn danger" onClick={() => remove(q)}>Delete</button>
          </div>
        )
      ))}
      <div style={{ marginTop: 12 }}>
        {editing === "new"
          ? <QuestionForm initial={null} nextOrder={nextOrder} onSave={(p) => save(p, null)} onCancel={() => setEditing(null)} />
          : <button className="ad-btn" onClick={() => setEditing("new")}>+ Add a question</button>}
      </div>
    </div>
  );
}

function StepEditor({ step, open, onToggle, reloadContent, say }) {
  const [d, setD] = useState({
    order_index: step.order_index, title: step.title, duration: step.duration, description: step.description,
    videoTitle: step.videoTitle, videoChannel: step.videoChannel, videoUrl: step.videoUrl, certLabel: step.certLabel, certUrl: step.certUrl,
  });
  const [newTopic, setNewTopic] = useState({ title: "", description: "" });
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });

  async function save() {
    try {
      await apiFetch(`/admin/modules/${step.id}`, { method: "PUT", body: JSON.stringify({ ...d, order_index: Number(d.order_index) || 0 }) });
      await reloadContent(); say("ok", "Step saved.");
    } catch (e) { say("err", e.message); }
  }
  async function remove() {
    if (!window.confirm(`Delete the step “${step.title}”?\n\nIts topic boxes, questions and learners' scores for it are deleted too.`)) return;
    try { await apiFetch(`/admin/modules/${step.id}`, { method: "DELETE" }); await reloadContent(); say("ok", "Step deleted."); }
    catch (e) { say("err", e.message); }
  }
  async function addTopic(e) {
    e.preventDefault();
    if (!newTopic.title.trim()) return;
    try {
      const next = (step.subtopics || []).length ? Math.max(...step.subtopics.map((s) => s.order_index)) + 1 : 1;
      await apiFetch("/admin/subtopics", { method: "POST", body: JSON.stringify({ module_id: step.id, order_index: next, title: newTopic.title.trim(), description: newTopic.description.trim() }) });
      setNewTopic({ title: "", description: "" });
      await reloadContent(); say("ok", "Topic box added.");
    } catch (err) { say("err", err.message); }
  }

  return (
    <div className="sp-card" style={{ borderRadius: 14, marginBottom: 12, overflow: "hidden" }}>
      <button onClick={onToggle} className="ad-step-head" aria-expanded={open}>
        <span className="sp-mono" style={{ fontSize: 11, opacity: 0.6, minWidth: 64 }}>{step.duration || "—"}</span>
        <strong style={{ flex: 1, textAlign: "left" }}>{step.title}</strong>
        <span style={{ fontSize: 12.5, opacity: 0.6 }}>{(step.subtopics || []).length} topics · {step.questionCount} questions</span>
        <span aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div style={{ padding: "4px 20px 20px" }}>
          <div className="flex flex-wrap" style={{ gap: 12 }}>
            <div style={{ flex: "0 0 90px" }}><AField label="Order"><input className="ad-input" type="number" value={d.order_index} onChange={set("order_index")} /></AField></div>
            <div style={{ flex: "1 1 220px" }}><AField label="Title"><input className="ad-input" value={d.title} onChange={set("title")} /></AField></div>
            <div style={{ flex: "0 0 140px" }}><AField label="Duration" hint="e.g. WK 1–2"><input className="ad-input" value={d.duration} onChange={set("duration")} /></AField></div>
          </div>
          <AField label="Description"><textarea className="ad-input" rows={2} value={d.description} onChange={set("description")} /></AField>
          <div className="flex flex-wrap" style={{ gap: 12 }}>
            <div style={{ flex: "1 1 220px" }}><AField label="Video title"><input className="ad-input" value={d.videoTitle} onChange={set("videoTitle")} /></AField></div>
            <div style={{ flex: "1 1 160px" }}><AField label="Video channel"><input className="ad-input" value={d.videoChannel} onChange={set("videoChannel")} /></AField></div>
          </div>
          <AField label="Video link" hint="A YouTube watch link, e.g. https://www.youtube.com/watch?v=…"><input className="ad-input" value={d.videoUrl} onChange={set("videoUrl")} /></AField>
          <div className="flex flex-wrap" style={{ gap: 12 }}>
            <div style={{ flex: "1 1 220px" }}><AField label="Free certification name"><input className="ad-input" value={d.certLabel} onChange={set("certLabel")} /></AField></div>
            <div style={{ flex: "1 1 260px" }}><AField label="Free certification link"><input className="ad-input" value={d.certUrl} onChange={set("certUrl")} /></AField></div>
          </div>
          <div className="flex" style={{ gap: 8, marginBottom: 22 }}>
            <button className="sp-btn-blaze" style={{ border: "none", borderRadius: 8, padding: "8px 18px", fontWeight: 600, cursor: "pointer" }} onClick={save}>Save step</button>
            <button className="ad-btn danger" onClick={remove}>Delete step</button>
          </div>

          <h4 className="sp-display" style={{ fontSize: 16, fontWeight: 600, marginBottom: 10 }}>Topic boxes</h4>
          {(step.subtopics || []).map((s) => <TopicRow key={s.id} sub={s} reloadContent={reloadContent} say={say} />)}
          <form onSubmit={addTopic} className="flex flex-wrap items-center" style={{ gap: 8, marginTop: 6, marginBottom: 24 }}>
            <input className="ad-input" style={{ flex: "1 1 160px" }} placeholder="New topic title" value={newTopic.title} onChange={(e) => setNewTopic({ ...newTopic, title: e.target.value })} />
            <input className="ad-input" style={{ flex: "2 1 240px" }} placeholder="One-line description" value={newTopic.description} onChange={(e) => setNewTopic({ ...newTopic, description: e.target.value })} />
            <button type="submit" className="ad-btn">+ Add topic</button>
          </form>

          <h4 className="sp-display" style={{ fontSize: 16, fontWeight: 600, marginBottom: 10 }}>Assessment questions</h4>
          <QuestionManager step={step} reloadContent={reloadContent} say={say} />
        </div>
      )}
    </div>
  );
}

function SkillBlock({ skill, reloadContent, say }) {
  const [d, setD] = useState({ name: skill.name, tagline: skill.tagline || "" });
  const [open, setOpen] = useState(null);
  const [ns, setNs] = useState({ title: "", duration: "", description: "" });

  async function save() {
    try { await apiFetch(`/admin/skills/${skill.id}`, { method: "PUT", body: JSON.stringify(d) }); await reloadContent(); say("ok", "Skill saved."); }
    catch (e) { say("err", e.message); }
  }
  async function remove() {
    if (!window.confirm(`Delete the whole skill “${skill.name}”?\n\nAll its steps, topic boxes, questions, learners' scores and certificates for it will be deleted. This can't be undone.`)) return;
    try { await apiFetch(`/admin/skills/${skill.id}`, { method: "DELETE" }); await reloadContent(); say("ok", "Skill deleted."); }
    catch (e) { say("err", e.message); }
  }
  async function addStep(e) {
    e.preventDefault();
    if (!ns.title.trim()) return say("err", "Give the new step a title.");
    try {
      const next = skill.modules.length ? Math.max(...skill.modules.map((m) => m.order_index)) + 1 : 1;
      const created = await apiFetch("/admin/modules", { method: "POST", body: JSON.stringify({ skill_id: skill.id, order_index: next, title: ns.title.trim(), duration: ns.duration.trim(), description: ns.description.trim() }) });
      setNs({ title: "", duration: "", description: "" });
      await reloadContent();
      setOpen(created.id);
      say("ok", "Step added. Open it to add the video, topic boxes and questions.");
    } catch (err) { say("err", err.message); }
  }

  return (
    <div>
      <div className="sp-card" style={{ borderRadius: 14, padding: 20, marginBottom: 22 }}>
        <h3 className="sp-display" style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Skill details</h3>
        <AField label="Name"><input className="ad-input" value={d.name} onChange={(e) => setD({ ...d, name: e.target.value })} /></AField>
        <AField label="One-line description"><input className="ad-input" value={d.tagline} onChange={(e) => setD({ ...d, tagline: e.target.value })} /></AField>
        <div className="flex items-center flex-wrap" style={{ gap: 8 }}>
          <button className="sp-btn-blaze" style={{ border: "none", borderRadius: 8, padding: "8px 18px", fontWeight: 600, cursor: "pointer" }} onClick={save}>Save skill</button>
          <button className="ad-btn danger" onClick={remove}>Delete skill</button>
          <span style={{ fontSize: 12, opacity: 0.55 }}>Internal key: <code>{skill.key}</code></span>
        </div>
      </div>

      <h3 className="sp-display" style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Steps ({skill.modules.length})</h3>
      {skill.modules.map((m) => (
        <StepEditor key={m.id} step={m} open={open === m.id} onToggle={() => setOpen(open === m.id ? null : m.id)} reloadContent={reloadContent} say={say} />
      ))}

      <form onSubmit={addStep} className="sp-card" style={{ borderRadius: 14, padding: 20, marginTop: 8 }}>
        <h4 className="sp-display" style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Add a step</h4>
        <div className="flex flex-wrap" style={{ gap: 12 }}>
          <div style={{ flex: "2 1 220px" }}><AField label="Title"><input className="ad-input" value={ns.title} onChange={(e) => setNs({ ...ns, title: e.target.value })} /></AField></div>
          <div style={{ flex: "0 0 140px" }}><AField label="Duration"><input className="ad-input" placeholder="WK 3" value={ns.duration} onChange={(e) => setNs({ ...ns, duration: e.target.value })} /></AField></div>
        </div>
        <AField label="Description"><textarea className="ad-input" rows={2} value={ns.description} onChange={(e) => setNs({ ...ns, description: e.target.value })} /></AField>
        <button type="submit" className="ad-btn">+ Add step</button>
      </form>
    </div>
  );
}

function AdminContent({ roadmaps, reloadContent, say }) {
  const [sel, setSel] = useState(Object.keys(roadmaps)[0] || null);
  const [ns, setNs] = useState({ name: "", tagline: "" });
  useEffect(() => { if (!sel || !roadmaps[sel]) setSel(Object.keys(roadmaps)[0] || null); }, [roadmaps, sel]);
  const skill = sel ? roadmaps[sel] : null;

  async function addSkill(e) {
    e.preventDefault();
    const key = slugify(ns.name);
    if (key.length < 2) return say("err", "Give the new skill a name first.");
    try {
      await apiFetch("/admin/skills", { method: "POST", body: JSON.stringify({ key, name: ns.name.trim(), tagline: ns.tagline.trim() }) });
      await reloadContent();
      setSel(key);
      say("ok", `Added “${ns.name.trim()}”. Now add its steps.`);
      setNs({ name: "", tagline: "" });
    } catch (err) { say("err", err.message); }
  }

  return (
    <div className="ad-grid">
      <aside>
        <p className="sp-mono" style={{ fontSize: 10.5, opacity: 0.6, marginBottom: 8 }}>SKILLS</p>
        <div className="flex flex-col" style={{ gap: 6 }}>
          {Object.entries(roadmaps).map(([key, s]) => (
            <button key={key} onClick={() => setSel(key)} className={`ad-skill ${sel === key ? "is-on" : ""}`}>
              <span>{s.name}</span><span style={{ fontSize: 11.5, opacity: 0.65 }}>{s.modules.length} steps</span>
            </button>
          ))}
        </div>
        <form onSubmit={addSkill} className="sp-card" style={{ borderRadius: 12, padding: 14, marginTop: 14 }}>
          <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>Add a skill</p>
          <input className="ad-input" style={{ marginBottom: 8 }} placeholder="Name, e.g. Docker Basics" value={ns.name} onChange={(e) => setNs({ ...ns, name: e.target.value })} aria-label="New skill name" />
          <input className="ad-input" style={{ marginBottom: 8 }} placeholder="One-line description" value={ns.tagline} onChange={(e) => setNs({ ...ns, tagline: e.target.value })} aria-label="New skill description" />
          <button type="submit" className="ad-btn" style={{ width: "100%" }}>+ Add skill</button>
        </form>
      </aside>
      <section style={{ minWidth: 0 }}>
        {skill ? <SkillBlock key={skill.id} skill={skill} reloadContent={reloadContent} say={say} /> : <p style={{ opacity: 0.7 }}>Pick a skill, or add one.</p>}
      </section>
    </div>
  );
}

function AdminAccount({ user, say }) {
  const [f, setF] = useState({ old_password: "", new_password: "", again: "" });
  async function submit(e) {
    e.preventDefault();
    if (f.new_password !== f.again) return say("err", "The two new passwords don't match.");
    try {
      await apiFetch("/change-password", { method: "POST", body: JSON.stringify({ old_password: f.old_password, new_password: f.new_password }) });
      setF({ old_password: "", new_password: "", again: "" });
      say("ok", "Password changed. Use the new one next time you sign in.");
    } catch (err) { say("err", err.message); }
  }
  return (
    <form onSubmit={submit} className="sp-card" style={{ borderRadius: 14, padding: 22, maxWidth: 440 }}>
      <h3 className="sp-display" style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>Change password</h3>
      <p style={{ fontSize: 13, opacity: 0.7, marginBottom: 16 }}>Signed in as {user.email}. If you're still using the starter password (admin123), change it now.</p>
      <AField label="Current password"><input className="ad-input" type="password" value={f.old_password} onChange={(e) => setF({ ...f, old_password: e.target.value })} autoComplete="current-password" /></AField>
      <AField label="New password" hint="At least 6 characters"><input className="ad-input" type="password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} autoComplete="new-password" /></AField>
      <AField label="New password again"><input className="ad-input" type="password" value={f.again} onChange={(e) => setF({ ...f, again: e.target.value })} autoComplete="new-password" /></AField>
      <button type="submit" className="sp-btn-blaze" style={{ border: "none", borderRadius: 8, padding: "9px 20px", fontWeight: 600, cursor: "pointer" }}>Change password</button>
    </form>
  );
}

function AdminConsole({ user, roadmaps, reloadContent, onClose }) {
  const [tab, setTab] = useState("overview");
  const [notice, setNotice] = useState(null);
  const say = (type, text) => setNotice({ type, text });
  useEffect(() => {
    if (!notice) return undefined;
    const t = setTimeout(() => setNotice(null), 6500);
    return () => clearTimeout(t);
  }, [notice]);

  const tabs = [["overview", "Overview"], ["users", "Users"], ["content", "Content"], ["account", "My account"]];
  return (
    <div className="ad-overlay" role="dialog" aria-modal="true" aria-label="Admin console">
      <div className="ad-bar">
        <div className="flex items-center" style={{ gap: 10 }}>
          <ShieldCheck size={21} style={{ color: "var(--blaze)" }} />
          <strong className="sp-display" style={{ fontSize: 19 }}>SkillPath Admin</strong>
          <span style={{ opacity: 0.65, fontSize: 13 }}>{user.name}</span>
        </div>
        <div className="flex flex-wrap" style={{ gap: 8 }}>
          {tabs.map(([id, label]) => (
            <button key={id} className={`ad-tab ${tab === id ? "is-on" : ""}`} onClick={() => setTab(id)}>{label}</button>
          ))}
        </div>
        <button className="ad-tab" onClick={onClose}>← Back to site</button>
      </div>
      <div className="ad-wrap">
        {notice && <div className={`ad-notice ${notice.type}`} role="status">{notice.text}</div>}
        {tab === "overview" && <AdminOverview say={say} />}
        {tab === "users" && <AdminUsers me={user} say={say} />}
        {tab === "content" && <AdminContent roadmaps={roadmaps} reloadContent={reloadContent} say={say} />}
        {tab === "account" && <AdminAccount user={user} say={say} />}
      </div>
    </div>
  );
}

export default function SkillPathSite() {
  const [query, setQuery] = useState("");
  const [activeKey, setActiveKey] = useState(null);
  const [searchError, setSearchError] = useState("");
  const [completed, setCompleted] = useState({});
  const [bookmarked, setBookmarked] = useState({});
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [authMode, setAuthMode] = useState("login"); // "login" | "register"
  const [nameInput, setNameInput] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authNotice, setAuthNotice] = useState("");
  const [skillList, setSkillList] = useState([]); // [{key, name, tagline}]
  const [roadmaps, setRoadmaps] = useState({});   // {key: {name, tagline, modules}}
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(true);
  const roadmapRef = useRef(null);
  const [selectedModule, setSelectedModule] = useState(null); // step shown in the detail panel
  const [selectedSub, setSelectedSub] = useState(null);       // topic (inside that step), if one was clicked
  const [view, setView] = useState("roadmap");               // "roadmap" | "videos"
  const [videoFocus, setVideoFocus] = useState(null);         // step id whose videos should be listed first
  const closePanel = () => { setSelectedModule(null); setSelectedSub(null); };
  const [results, setResults] = useState({});               // {moduleId: {best, total, passed, attempts}}
  const [certificates, setCertificates] = useState([]);     // certificates this user has earned
  const [assessment, setAssessment] = useState(null);       // the open assessment (questions, answers, result)
  const [certView, setCertView] = useState(null);           // certificate being displayed
  const [showAdmin, setShowAdmin] = useState(false);          // admin console open?

  // Re-reads every skill/step/topic/question count from the server (used after an admin edits content).
  async function reloadContent() {
    const list = await apiFetch("/skills");
    const details = await Promise.all(list.map((s) => apiFetch(`/skills/${s.key}`)));
    const combined = {};
    list.forEach((s, i) => { combined[s.key] = details[i]; });
    setSkillList(list);
    setRoadmaps(combined);
    setActiveKey((k) => (k && !combined[k] ? null : k));
    setSelectedModule(null);
    setSelectedSub(null);
  }

  function applyUserData({ results: res, certificates: certs, bookmarkIds }) {
    setResults(res);
    setCompleted(Object.fromEntries(Object.entries(res).filter(([, v]) => v.passed).map(([id]) => [id, true])));
    setCertificates(certs);
    setBookmarked(Object.fromEntries(bookmarkIds.map((id) => [id, true])));
  }

  // Load everything once: who's logged in, every skill + its full roadmap,
  // and (if logged in) that user's saved progress and bookmarks.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const meData = await apiFetch("/me");
        if (cancelled) return;
        setUser(meData.user);

        // Start loading this user's progress right away, in parallel with the roadmaps.
        const userDataPromise = meData.user ? fetchUserData() : null;
        if (userDataPromise) userDataPromise.catch(() => {});

        const list = await apiFetch("/skills");
        if (cancelled) return;
        setSkillList(list);

        const details = await Promise.all(list.map((s) => apiFetch(`/skills/${s.key}`)));
        if (cancelled) return;
        const combined = {};
        list.forEach((s, i) => { combined[s.key] = details[i]; });
        setRoadmaps(combined);

        if (userDataPromise) {
          const userData = await userDataPromise;
          if (cancelled) return;
          applyUserData(userData);
        }
      } catch (err) {
        if (!cancelled) {
          setApiError(
            "Can't reach the SkillPath server. Make sure the backend is running (python app.py on port 5000)."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  function goToSkill(key) {
    setActiveKey(key);
    setView("roadmap");
    setVideoFocus(null);
    setSearchError("");
    requestAnimationFrame(() => {
      roadmapRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function handleSearch(e) {
    e.preventDefault();
    const q = query.trim().toLowerCase();
    if (!q) return;
    const match = skillList.find(
      (skill) =>
        skill.name.toLowerCase().includes(q) ||
        (ALIASES[skill.key] || []).some((a) => a.includes(q) || q.includes(a))
    );
    if (match) {
      goToSkill(match.key);
    } else {
      setSearchError(
        "No roadmap yet for that — try Python, Data Science, AWS, Web Development, or Cybersecurity."
      );
    }
  }

  function sessionLost() {
    setAssessment(null);
    setUser(null);
    setAuthNotice("Your login wasn't kept — please sign in again.");
    setAuthMode("login");
    setShowLogin(true);
  }

  // "Mark as reached" starts the step's assessment. Passing it is what marks the step as reached.
  async function openAssessment(m) {
    if (!user) { setAuthNotice("Sign in to take the assessment for this step."); setAuthMode("login"); setShowLogin(true); return; }
    setAssessment({ module: m, loading: true, error: "", data: null, answers: {}, current: 0, submitting: false, result: null });
    try {
      const data = await apiFetch(`/modules/${m.id}/assessment`);
      const answers = {};
      data.questions.forEach((q) => { if (q.kind === "code") answers[q.id] = q.starter || ""; });
      setAssessment((p) => (p && p.module.id === m.id ? { ...p, loading: false, data, answers } : p));
    } catch (err) {
      if (err.status === 401) sessionLost();
      else setAssessment((p) => (p ? { ...p, loading: false, error: err.message || "Couldn't load the assessment." } : p));
    }
  }

  function setAssessmentAnswer(qid, value) {
    setAssessment((p) => (p ? { ...p, answers: { ...p.answers, [qid]: value } } : p));
  }

  function retakeAssessment() {
    setAssessment((p) => {
      if (!p || !p.data) return p;
      const answers = {};
      p.data.questions.forEach((q) => { if (q.kind === "code") answers[q.id] = q.starter || ""; });
      return { ...p, answers, current: 0, result: null, error: "" };
    });
  }

  async function submitAssessment() {
    const st = assessment;
    if (!st || st.submitting) return;
    setAssessment({ ...st, submitting: true, error: "" });
    try {
      const res = await apiFetch(`/modules/${st.module.id}/assessment`, { method: "POST", body: JSON.stringify({ answers: st.answers }) });
      setAssessment((p) => (p ? { ...p, submitting: false, result: res } : p));
      const fresh = await apiFetch("/results");
      setResults(fresh);
      setCompleted(Object.fromEntries(Object.entries(fresh).filter(([, v]) => v.passed).map(([id]) => [id, true])));
      if (res.certificate) {
        setCertificates((prev) => (prev.some((c) => c.code === res.certificate.code) ? prev : [...prev, res.certificate]));
      }
    } catch (err) {
      if (err.status === 401) sessionLost();
      else setAssessment((p) => (p ? { ...p, submitting: false, error: err.message || "Couldn't submit your answers." } : p));
    }
  }

  async function toggleBookmark(moduleId) {
    if (!user) { setAuthNotice("Sign in to bookmark a stop."); setShowLogin(true); return; }
    try {
      const res = await apiFetch(`/bookmarks/${moduleId}`, { method: "POST" });
      setBookmarked((prev) => ({ ...prev, [moduleId]: res.bookmarked }));
    } catch (err) {
      if (err.status === 401) {
        setUser(null);
        setAuthNotice("Your login wasn't kept — please sign in again.");
        setAuthMode("login");
        setShowLogin(true);
      } else {
        setApiError("Couldn't save that bookmark — check the backend is running.");
      }
    }
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    setAuthError("");
    try {
      const payload = { email: emailInput.trim(), password: passwordInput };
      let data;
      if (authMode === "register") {
        data = await apiFetch("/register", { method: "POST", body: JSON.stringify({ ...payload, name: nameInput.trim() }) });
      } else {
        data = await apiFetch("/login", { method: "POST", body: JSON.stringify(payload) });
      }
      let userData;
      try {
        userData = await fetchUserData();
      } catch (err) {
        if (err.status === 401) {
          setUser(null);
          setAuthError(
            "Signed in, but your browser didn't keep the login. Open the site at http://127.0.0.1:5173 and try again."
          );
          return;
        }
        throw err;
      }
      setUser(data.user);
      setShowLogin(false);
      setAuthNotice("");
      setNameInput(""); setEmailInput(""); setPasswordInput("");
      applyUserData(userData);
    } catch (err) {
      setAuthError(err.message || "Something went wrong.");
    }
  }

  async function handleLogout() {
    try { await apiFetch("/logout", { method: "POST" }); } catch {}
    setUser(null);
    setCompleted({});
    setBookmarked({});
    setResults({});
    setCertificates([]);
    setAssessment(null);
    setCertView(null);
    setShowAdmin(false);
  }

  const active = activeKey ? roadmaps[activeKey] : null;
  const activeCompletedCount = active ? active.modules.filter((m) => completed[m.id]).length : 0;
  const activePct = active ? Math.round((activeCompletedCount / active.modules.length) * 100) : 0;

  const bookmarkList = [];
  Object.entries(roadmaps).forEach(([key, skill]) => {
    skill.modules.forEach((m) => {
      if (bookmarked[m.id]) bookmarkList.push({ key, skillName: skill.name, module: m });
    });
  });

  return (
    <div className="sp-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,700;1,9..144,500&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

        .sp-root {
          --forest: #1F3A2E;
          --forest-deep: #12241C;
          --paper: #EFEBDD;
          --card: #FBF9F0;
          --blaze: #D69A2D;
          --teal: #2F6B63;
          --ink: #1B2A22;
          --line: #D8D2BE;
          font-family: 'Inter', sans-serif;
          background: var(--paper);
          color: var(--ink);
        }
        .sp-root * { box-sizing: border-box; }
        .sp-display { font-family: 'Fraunces', serif; }
        .sp-mono { font-family: 'JetBrains Mono', monospace; letter-spacing: 0.04em; }

        .sp-bg-forest { background-color: var(--forest); }
        .sp-bg-paper { background-color: var(--paper); }
        .sp-bg-card { background-color: var(--card); }
        .sp-text-blaze { color: var(--blaze); }
        .sp-text-teal { color: var(--teal); }
        .sp-text-paper { color: var(--paper); }
        .sp-text-ink { color: var(--ink); }
        .sp-border-line { border-color: var(--line); }

        .sp-btn-blaze {
          background: var(--blaze);
          color: var(--forest-deep);
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .sp-btn-blaze:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(214,154,45,0.35); }
        .sp-btn-blaze:focus-visible, .sp-chip:focus-visible, .sp-link-btn:focus-visible, .sp-icon-btn:focus-visible, .sp-input:focus-visible {
          outline: 2px solid var(--blaze); outline-offset: 2px;
        }

        .sp-chip {
          border: 1px solid rgba(239,235,221,0.35);
          color: var(--paper);
          transition: background 0.15s ease, border-color 0.15s ease;
        }
        .sp-chip:hover { background: rgba(239,235,221,0.1); border-color: var(--blaze); }

        .sp-card {
          background: var(--card);
          border: 1px solid var(--line);
        }

        .sp-link-btn {
          border: 1px solid var(--line);
          background: var(--paper);
          color: var(--ink);
          transition: border-color 0.15s ease, background 0.15s ease;
        }
        .sp-link-btn:hover { border-color: var(--teal); background: var(--card); }

        .sp-progress-track { background: var(--line); }
        .sp-progress-fill { background: var(--blaze); transition: width 0.4s ease; }

        .sp-contour {
          position: absolute; inset: 0; opacity: 0.16; pointer-events: none;
        }

        .sp-fade-in { animation: spFadeIn 0.5s ease both; }
        @keyframes spFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        @media (prefers-reduced-motion: reduce) {
          .sp-fade-in, .sp-btn-blaze, .sp-chip, .sp-link-btn, .sp-progress-fill { animation: none !important; transition: none !important; }
        }

        .sp-icon-btn { transition: background 0.15s ease, color 0.15s ease; }

        /* ---- roadmap.sh-style roadmap ---- */
        .rs-canvas { background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 36px 24px 32px; overflow-x: auto; }
        .rs-wrap { position: relative; min-width: 760px; }
        .rs-svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
        .rs-title {
          position: relative; z-index: 1; display: table; margin: 0 auto 48px; background: #111; color: #fff;
          font-weight: 700; font-size: 16px; padding: 10px 24px; border-radius: 8px;
        }
        .rs-row {
          position: relative; z-index: 1; display: grid; grid-template-columns: 1fr auto 1fr;
          column-gap: 96px; align-items: center; margin-bottom: 60px;
        }
        .rs-row:last-child { margin-bottom: 0; }
        .rs-col { display: flex; flex-direction: column; gap: 12px; }
        .rs-col.left { align-items: flex-end; }
        .rs-col.right { align-items: flex-start; }

        .rs-main {
          position: relative; z-index: 1; font: inherit; color: #111; cursor: pointer; text-align: center;
          display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 220px;
          padding: 12px 24px; background: #FFE599; border: 2px solid #111; border-radius: 8px;
          box-shadow: 0 3px 0 #111; transition: background 0.15s ease, transform 0.15s ease;
        }
        .rs-main:hover { background: #FFD966; transform: translateY(-1px); }
        .rs-main .t { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; }
        .rs-main .d { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 0.06em; opacity: 0.65; }
        .rs-main.is-done { background: #B8E3C5; }
        .rs-main.is-done:hover { background: #A5D8B5; }

        .rs-sub {
          position: relative; z-index: 1; font: inherit; font-size: 14px; font-weight: 500; color: #111; cursor: pointer;
          text-align: left; max-width: 250px; padding: 9px 14px; background: #FFF3C4; border: 2px solid #111;
          border-radius: 8px; transition: background 0.15s ease;
        }
        .rs-sub:hover { background: #FFE699; }
        .rs-sub.is-covered { background: #DDF1E3; }
        .rs-sub.is-covered:hover { background: #CBE9D3; }

        .rs-narrow-subs {
          margin: 10px 0 0 18px; padding-left: 16px; border-left: 2px dashed #111;
          display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
        }

        .rs-legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 12.5px; opacity: 0.8; margin-bottom: 14px; }
        .rs-legend .sw { display: inline-block; width: 16px; height: 12px; border: 2px solid #111; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }

        .rs-tab {
          display: inline-flex; align-items: center; gap: 7px; padding: 8px 16px; border-radius: 999px;
          border: 1.5px solid var(--line); background: transparent; font: inherit; font-size: 14px; font-weight: 600;
          color: var(--ink); cursor: pointer; transition: background 0.15s ease, color 0.15s ease;
        }
        .rs-tab:hover { background: rgba(31,58,46,0.06); }
        .rs-tab.is-on { background: var(--forest); border-color: var(--forest); color: #F4F1E4; }
        .rs-count { font-size: 11.5px; padding: 1px 7px; border-radius: 999px; background: rgba(127,127,127,0.22); }
        /* ---- assessment ---- */
        .as-overlay { position: fixed; inset: 0; z-index: 80; background: rgba(18,36,28,0.62); display: flex; align-items: center; justify-content: center; padding: 16px; }
        .as-dialog { width: 100%; max-width: 780px; max-height: 92vh; overflow-y: auto; background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 26px 28px; }
        .as-opt {
          display: flex; align-items: flex-start; gap: 12px; width: 100%; text-align: left; padding: 12px 14px;
          border: 2px solid var(--line); border-radius: 12px; background: #fff; font: inherit; font-size: 15px;
          color: var(--ink); cursor: pointer; transition: border-color 0.15s ease, background 0.15s ease;
        }
        .as-opt:hover { border-color: var(--teal); }
        .as-opt.is-picked { border-color: var(--teal); background: rgba(47,107,99,0.09); }
        .as-opt .ltr {
          flex: none; width: 26px; height: 26px; border-radius: 50%; border: 1.5px solid currentColor;
          display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;
          font-family: 'JetBrains Mono', monospace;
        }
        .as-opt.is-picked .ltr { background: var(--teal); border-color: var(--teal); color: #fff; }
        .as-dot {
          width: 32px; height: 32px; border-radius: 8px; border: 1.5px solid var(--line); background: #fff;
          font: inherit; font-size: 12.5px; font-weight: 600; color: var(--ink); cursor: pointer;
        }
        .as-dot.is-answered { background: rgba(47,107,99,0.13); border-color: var(--teal); }
        .as-dot.is-current { background: var(--forest); border-color: var(--forest); color: #fff; }
        .as-code {
          width: 100%; min-height: 220px; resize: vertical; padding: 14px; border: 2px solid var(--line); border-radius: 12px;
          background: #14221b; color: #E8F0E4; font-family: 'JetBrains Mono', monospace; font-size: 13.5px; line-height: 1.55; tab-size: 4;
        }
        .as-code:focus { outline: none; border-color: var(--blaze); }
        .as-pre {
          margin: 0; padding: 12px 14px; border-radius: 10px; background: #14221b; color: #E8F0E4; overflow-x: auto;
          font-family: 'JetBrains Mono', monospace; font-size: 12.5px; line-height: 1.55; white-space: pre;
        }
        @media (max-width: 560px) { .as-dialog { padding: 20px 16px; } }

        /* ---- certificate (sizes use container units so it scales when printed) ---- */
        .cert-overlay { position: fixed; inset: 0; z-index: 90; background: #14221b; overflow: auto; padding: 18px 18px 40px; display: flex; flex-direction: column; align-items: center; gap: 14px; }
        .cert-toolbar { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
        .cert-print { width: 100%; max-width: 1040px; min-width: 720px; }   /* phones scroll sideways instead of shrinking the text */
        .cert-sheet {
          container-type: inline-size; width: 100%; aspect-ratio: 1.4142 / 1; background: #FFFDF6; padding: 2.4%;
          box-shadow: 0 20px 60px rgba(0,0,0,0.45); font-family: 'Fraunces', Georgia, serif; color: #1B2A22;
        }
        .cert-frame {
          height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
          border: 3px solid #1F3A2E; box-shadow: inset 0 0 0 7px #FFFDF6, inset 0 0 0 8px #D69A2D; padding: 2% 6%;
        }
        .cert-brand { display: flex; align-items: center; gap: 1.2cqw; font-weight: 700; color: #1F3A2E; font-size: 3cqw; }
        .cert-brand-icon { width: 3.2cqw; height: 3.2cqw; color: #D69A2D; }
        .cert-kicker { margin-top: 2cqw; letter-spacing: 0.35em; font-size: 1.6cqw; color: #9A6A12; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .cert-small { font-family: 'Inter', sans-serif; font-size: 1.6cqw; margin-top: 1.6cqw; color: #3B4A41; }
        .cert-name { font-style: italic; font-weight: 600; font-size: 6cqw; line-height: 1.1; margin-top: 0.8cqw; overflow-wrap: anywhere; }
        .cert-rule { width: 38%; height: 2px; background: #D69A2D; margin-top: 1cqw; }
        .cert-skill { font-size: 4cqw; font-weight: 700; color: #1F3A2E; margin-top: 0.8cqw; line-height: 1.15; }
        .cert-footer { width: 100%; display: flex; justify-content: space-between; align-items: center; margin-top: 2.6cqw; gap: 2cqw; }
        .cert-foot-col { flex: 1; text-align: center; }
        .cert-foot-label { font-family: 'JetBrains Mono', monospace; font-size: 1.1cqw; letter-spacing: 0.2em; color: #6B7A70; }
        .cert-foot-value { font-family: 'Inter', sans-serif; font-size: 1.7cqw; font-weight: 600; margin-top: 0.5cqw; border-top: 1px solid #1F3A2E; padding-top: 0.6cqw; display: inline-flex; align-items: center; justify-content: center; min-height: 3.6cqw; min-width: 60%; }
        .cert-code { font-family: 'JetBrains Mono', monospace; font-size: 1.4cqw; }
        .cert-seal {
          flex: none; width: 8.5cqw; height: 8.5cqw; border-radius: 50%; display: flex; align-items: center; justify-content: center;
          background: radial-gradient(circle at 35% 30%, #F0C860, #D69A2D 60%, #A87414); box-shadow: 0 0 0 0.5cqw #FFFDF6, 0 0 0 0.7cqw #D69A2D;
        }
        .cert-seal-icon { width: 4.6cqw; height: 4.6cqw; color: #1F3A2E; }
        .cert-verify { font-family: 'Inter', sans-serif; font-size: 1.1cqw; color: #6B7A70; margin-top: 1.8cqw; }

        @media print {
          @page { size: A4 landscape; margin: 0; }
          html, body { background: #fff !important; }
          .sp-root > :not(.cert-overlay) { display: none !important; }
          .cert-overlay { position: static !important; background: #fff !important; padding: 0 !important; overflow: visible !important; display: block !important; }
          .no-print { display: none !important; }
          .cert-print { max-width: none !important; width: 100vw !important; }
          .cert-sheet { width: 100vw !important; height: 100vh !important; aspect-ratio: auto !important; box-shadow: none !important; }
          * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
        /* ---- admin console ---- */
        .ad-overlay { position: fixed; inset: 0; z-index: 85; background: var(--paper); overflow-y: auto; }
        .ad-bar {
          position: sticky; top: 0; z-index: 5; background: var(--forest); color: #F4F1E4; display: flex; align-items: center;
          justify-content: space-between; gap: 14px; flex-wrap: wrap; padding: 12px 22px;
        }
        .ad-tab {
          padding: 7px 16px; border-radius: 999px; border: 1.5px solid rgba(244,241,228,0.35); background: transparent;
          color: #F4F1E4; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.15s ease, color 0.15s ease;
        }
        .ad-tab:hover { background: rgba(244,241,228,0.12); }
        .ad-tab.is-on { background: #F4F1E4; color: var(--forest); border-color: #F4F1E4; }
        .ad-wrap { max-width: 1120px; margin: 0 auto; padding: 28px 20px 90px; color: var(--ink); }
        .ad-notice { position: sticky; top: 70px; z-index: 4; margin-bottom: 18px; padding: 11px 16px; border-radius: 10px; font-size: 14px; font-weight: 500; }
        .ad-notice.ok { background: #DDF1E3; border: 1px solid #2F8F5B; color: #1F5C3A; }
        .ad-notice.err { background: #F8E4E0; border: 1px solid #B5483A; color: #8E2F23; }
        .ad-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .ad-table th { text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 0.06em; opacity: 0.6; padding: 10px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
        .ad-table td { padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: middle; }
        .ad-table tr:last-child td { border-bottom: none; }
        .ad-input { width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; font: inherit; font-size: 14px; background: #fff; color: var(--ink); }
        .ad-input:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(47,107,99,0.15); }
        textarea.ad-input { resize: vertical; }
        .ad-mono { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
        .ad-label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 4px; opacity: 0.75; }
        .ad-hint { display: block; font-size: 11.5px; opacity: 0.55; margin-top: 4px; line-height: 1.45; }
        .ad-btn {
          border: 1.5px solid var(--line); background: #fff; color: var(--ink); border-radius: 8px; padding: 6px 12px; font: inherit;
          font-size: 13px; font-weight: 600; cursor: pointer; transition: border-color 0.15s ease, background 0.15s ease;
        }
        .ad-btn:hover { border-color: var(--teal); background: rgba(47,107,99,0.06); }
        .ad-btn.danger { color: #B5483A; }
        .ad-btn.danger:hover { border-color: #B5483A; background: rgba(181,72,58,0.07); }
        .ad-badge { display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.06em; padding: 2px 8px; border-radius: 999px; background: rgba(27,42,34,0.1); }
        .ad-badge.is-admin { background: var(--blaze); color: var(--forest-deep); }
        .ad-grid { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 28px; align-items: start; }
        .ad-skill {
          display: flex; flex-direction: column; align-items: flex-start; gap: 2px; text-align: left; padding: 10px 14px; border-radius: 10px;
          border: 1.5px solid var(--line); background: #fff; font: inherit; font-size: 14.5px; font-weight: 600; color: var(--ink); cursor: pointer;
        }
        .ad-skill.is-on { background: var(--forest); color: #F4F1E4; border-color: var(--forest); }
        .ad-step-head { display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px 18px; border: none; background: transparent; font: inherit; font-size: 15px; color: var(--ink); text-align: left; cursor: pointer; }
        .ad-step-head:hover { background: rgba(31,58,46,0.04); }
        .ad-form { border: 1.5px dashed var(--line); border-radius: 12px; padding: 16px; margin: 10px 0; background: rgba(255,255,255,0.6); }
        @media (max-width: 820px) { .ad-grid { grid-template-columns: 1fr; } }
      `}</style>

      {/* ---------------- NAV ---------------- */}
      <header className="sp-bg-forest" style={{ position: "sticky", top: 0, zIndex: 40 }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }} className="flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2">
            <Compass size={22} className="sp-text-blaze" />
            <span className="sp-display sp-text-paper" style={{ fontSize: 20, fontWeight: 600 }}>
              SkillPath
            </span>
          </div>
          <nav className="flex items-center gap-5" style={{ fontSize: 14 }}>
            <a href="#how" className="sp-text-paper" style={{ opacity: 0.85, textDecoration: "none" }}>How it works</a>
            <a href="#roadmap" className="sp-text-paper" style={{ opacity: 0.85, textDecoration: "none" }}>Roadmaps</a>
            <a href="#progress" className="sp-text-paper" style={{ opacity: 0.85, textDecoration: "none" }}>Progress</a>
            {user ? (
              <span className="sp-text-paper flex items-center gap-2" style={{ fontSize: 14 }}>
                <span className="flex items-center gap-1"><MapPin size={15} className="sp-text-blaze" /> Hi, {user.name}</span>
                {user.role === "admin" && (
                  <button
                    onClick={() => setShowAdmin(true)}
                    className="sp-btn-blaze flex items-center gap-1"
                    style={{ border: "none", borderRadius: 999, padding: "5px 12px", fontSize: 12.5, fontWeight: 700, cursor: "pointer" }}
                  >
                    <ShieldCheck size={14} /> Admin console
                  </button>
                )}
                <button
                  onClick={handleLogout}
                  className="sp-icon-btn flex items-center gap-1"
                  style={{ border: "none", background: "transparent", cursor: "pointer", color: "inherit", opacity: 0.65, fontSize: 12.5 }}
                  title="Sign out"
                >
                  <LogOut size={13} /> Sign out
                </button>
              </span>
            ) : (
              <button
                onClick={() => { setAuthMode("login"); setAuthError(""); setShowLogin(true); }}
                className="sp-icon-btn flex items-center gap-1 px-3 py-1.5 rounded-full sp-text-paper"
                style={{ border: "1px solid rgba(239,235,221,0.35)", fontSize: 13, background: "transparent", cursor: "pointer" }}
              >
                <User size={14} /> Sign in
              </button>
            )}
          </nav>
        </div>
      </header>

      {apiError && (
        <div style={{ background: "#5A2E24", color: "#F6DCC9", fontSize: 13.5, textAlign: "center", padding: "8px 16px" }}>
          {apiError}
        </div>
      )}

      {/* ---------------- HERO ---------------- */}
      <section className="sp-bg-forest" style={{ position: "relative", overflow: "hidden" }}>
        <svg className="sp-contour" viewBox="0 0 1000 500" preserveAspectRatio="none">
          {[60, 130, 200, 270, 340, 410].map((y, i) => (
            <path
              key={i}
              d={`M0,${y} Q 150,${y - 30} 300,${y} T 600,${y} T 1000,${y}`}
              fill="none"
              stroke="#EFEBDD"
              strokeWidth="1"
            />
          ))}
        </svg>
        <div style={{ maxWidth: 1100, margin: "0 auto", position: "relative" }} className="px-5 pt-16 pb-20">
          <p className="sp-mono sp-text-blaze" style={{ fontSize: 12, marginBottom: 14 }}>
            FREE SKILL LEARNING &amp; CERTIFICATION ROADMAPS
          </p>
          <h1 className="sp-display sp-text-paper" style={{ fontSize: "clamp(34px, 5vw, 56px)", fontWeight: 600, lineHeight: 1.08, maxWidth: 680 }}>
            Every skill has a path. We'll help you find it.
          </h1>
          <p className="sp-text-paper" style={{ opacity: 0.8, fontSize: 17, maxWidth: 520, marginTop: 18, lineHeight: 1.6 }}>
            Search any skill and get a structured roadmap — with free video playlists
            and free certifications at every step, plus a tracker to keep you moving.
          </p>

          <form onSubmit={handleSearch} className="flex flex-wrap gap-2" style={{ marginTop: 32, maxWidth: 520 }}>
            <div className="flex items-center sp-bg-card" style={{ borderRadius: 999, padding: "4px 4px 4px 18px", flex: "1 1 260px" }}>
              <Search size={17} className="sp-text-teal" style={{ flexShrink: 0 }} />
              <input
                className="sp-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Try “Python” or “AWS”…"
                style={{ border: "none", outline: "none", background: "transparent", padding: "10px 10px", fontSize: 15, width: "100%", color: "var(--ink)" }}
              />
              <button type="submit" className="sp-btn-blaze" style={{ border: "none", borderRadius: 999, padding: "10px 18px", fontSize: 14, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
                Find path
              </button>
            </div>
          </form>
          {searchError && (
            <p className="sp-fade-in" style={{ color: "#F0B98A", fontSize: 13.5, marginTop: 10, maxWidth: 480 }}>
              {searchError}
            </p>
          )}

          <div className="flex flex-wrap gap-2" style={{ marginTop: 22 }}>
            {skillList.map((skill) => (
              <button key={skill.key} onClick={() => goToSkill(skill.key)} className="sp-chip" style={{ borderRadius: 999, padding: "7px 14px", fontSize: 13.5, background: "transparent", cursor: "pointer" }}>
                {skill.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- HOW IT WORKS ---------------- */}
      <section id="how" className="px-5" style={{ maxWidth: 1100, margin: "0 auto", padding: "64px 20px" }}>
        <p className="sp-mono sp-text-teal" style={{ fontSize: 12 }}>HOW SKILLPATH WORKS</p>
        <h2 className="sp-display" style={{ fontSize: 30, fontWeight: 600, marginTop: 8, marginBottom: 36 }}>
          Four steps, start to finish
        </h2>
        <div className="grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 28 }}>
          {HOW_IT_WORKS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i}>
                <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                  <span className="sp-mono sp-text-blaze" style={{ fontSize: 13 }}>0{i + 1}</span>
                  <div style={{ height: 1, flex: 1, background: "var(--line)" }} />
                  <Icon size={20} className="sp-text-teal" />
                </div>
                <h3 className="sp-display" style={{ fontSize: 19, fontWeight: 600, marginBottom: 6 }}>{step.title}</h3>
                <p style={{ fontSize: 14.5, opacity: 0.75, lineHeight: 1.55 }}>{step.text}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ---------------- ROADMAP ---------------- */}
      <section id="roadmap" ref={roadmapRef} className="sp-bg-card" style={{ borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "64px 20px" }}>
          {loading ? (
            <div className="sp-fade-in" style={{ textAlign: "center", padding: "40px 0", opacity: 0.7 }}>
              <p style={{ fontSize: 15 }}>Loading roadmaps from the server…</p>
            </div>
          ) : !active ? (
            <div className="sp-fade-in" style={{ textAlign: "center", padding: "40px 0" }}>
              <Milestone size={30} className="sp-text-teal" style={{ margin: "0 auto 14px" }} />
              <h2 className="sp-display" style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
                Search a skill to see its path
              </h2>
              <p style={{ opacity: 0.7, fontSize: 15, maxWidth: 420, margin: "0 auto" }}>
                Pick one of the quick trails up in the hero, or type a skill into the search bar.
              </p>
            </div>
          ) : (
            <div key={activeKey} className="sp-fade-in">
              <p className="sp-mono sp-text-teal" style={{ fontSize: 12 }}>ROADMAP</p>
              <h2 className="sp-display" style={{ fontSize: 30, fontWeight: 600, marginTop: 6 }}>{active.name}</h2>
              <p style={{ opacity: 0.75, fontSize: 15, marginTop: 6, maxWidth: 520 }}>{active.tagline}</p>

              <div style={{ marginTop: 22, marginBottom: 44 }}>
                <div className="flex items-center justify-between" style={{ fontSize: 13, marginBottom: 6 }}>
                  <span className="sp-mono">TRAIL PROGRESS</span>
                  <span className="sp-mono sp-text-blaze">{activeCompletedCount}/{active.modules.length} · {activePct}%</span>
                </div>
                <div className="sp-progress-track" style={{ height: 8, borderRadius: 999, overflow: "hidden" }}>
                  <div className="sp-progress-fill" style={{ height: "100%", width: `${activePct}%`, borderRadius: 999 }} />
                </div>
                {(() => {
                  const steps = active.modules.filter((m) => m.questionCount > 0);
                  const passedN = steps.filter((m) => completed[m.id]).length;
                  const cert = certificates.find((c) => c.skillKey === activeKey);
                  if (cert) {
                    return (
                      <div className="flex items-center justify-between flex-wrap" style={{ gap: 12, marginTop: 16, padding: "14px 18px", borderRadius: 12, background: "var(--forest)", color: "#F4F1E4" }}>
                        <span className="flex items-center" style={{ gap: 10, fontSize: 14.5 }}>
                          <Award size={22} style={{ color: "var(--blaze)", flexShrink: 0 }} />
                          You have earned the SkillPath certificate for {active.name}.
                        </span>
                        <button onClick={() => setCertView(cert)} className="sp-btn-blaze" style={{ border: "none", borderRadius: 10, padding: "8px 18px", fontWeight: 600, cursor: "pointer" }}>
                          View certificate
                        </button>
                      </div>
                    );
                  }
                  if (!steps.length) return null;
                  return (
                    <p style={{ fontSize: 13, opacity: 0.7, marginTop: 12 }}>
                      {user
                        ? `Pass the assessment on every step to earn your certificate — ${passedN} of ${steps.length} passed.`
                        : "Pass the assessment on every step to earn a SkillPath certificate. Sign in to begin."}
                    </p>
                  );
                })()}
              </div>

              <div className="flex items-center" style={{ gap: 8, marginBottom: 18, flexWrap: "wrap" }}>
                <button className={`rs-tab ${view === "roadmap" ? "is-on" : ""}`} onClick={() => { setView("roadmap"); setVideoFocus(null); }}>
                  <Milestone size={15} /> Roadmap
                </button>
                <button className={`rs-tab ${view === "videos" ? "is-on" : ""}`} onClick={() => setView("videos")}>
                  <PlayCircle size={15} /> Videos
                  <span className="rs-count">{new Set(active.modules.map((m) => m.videoUrl).filter(Boolean)).size}</span>
                </button>
              </div>

              {view === "roadmap" ? (
                <>
                  <div className="rs-legend">
                    <span><i className="sw" style={{ background: "#FFE599" }} />Roadmap step</span>
                    <span><i className="sw" style={{ background: "#FFF3C4" }} />Topic inside a step</span>
                    <span><i className="sw" style={{ background: "#B8E3C5" }} />Reached</span>
                    <span>Click any box for details</span>
                  </div>
                  <RoadmapGraph
                    skill={active}
                    completed={completed}
                    bookmarked={bookmarked}
                    onPickModule={(m) => { setSelectedModule(m); setSelectedSub(null); }}
                    onPickSub={(m, s) => { setSelectedModule(m); setSelectedSub(s); }}
                  />
                </>
              ) : (
                <VideosView
                  skill={active}
                  focusId={videoFocus}
                  onPickModule={(m) => { setSelectedModule(m); setSelectedSub(null); }}
                />
              )}
            </div>
          )}
        </div>
      </section>

      {/* ---------------- ROADMAP NODE DETAIL PANEL ---------------- */}
      {selectedModule && (
        <div
          onClick={closePanel}
          style={{ position: "fixed", inset: 0, background: "rgba(18,36,28,0.5)", zIndex: 55, display: "flex", justifyContent: "flex-end" }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="sp-bg-card sp-fade-in"
            style={{ width: "100%", maxWidth: 420, height: "100%", overflowY: "auto", padding: 28, borderLeft: "1px solid var(--line)" }}
          >
            <div className="flex items-center justify-between" style={{ marginBottom: 18 }}>
              <span className="sp-mono sp-text-teal" style={{ fontSize: 11.5 }}>
                {selectedSub ? "TOPIC" : selectedModule.duration}
              </span>
              <button onClick={closePanel} className="sp-icon-btn" style={{ border: "none", background: "transparent", cursor: "pointer" }} aria-label="Close">
                <X size={18} />
              </button>
            </div>

            <h3 className="sp-display" style={{ fontSize: 23, fontWeight: 600, marginBottom: 10 }}>
              {selectedSub ? selectedSub.title : selectedModule.title}
            </h3>

            {selectedSub ? (
              <>
                <p style={{ fontSize: 14.5, opacity: 0.8, lineHeight: 1.6, marginBottom: 14 }}>{selectedSub.description}</p>
                <p style={{ fontSize: 13, opacity: 0.75, marginBottom: 24 }}>
                  Part of{" "}
                  <button
                    onClick={() => setSelectedSub(null)}
                    style={{ border: "none", background: "none", padding: 0, cursor: "pointer", color: "var(--teal)", fontWeight: 600, fontSize: 13 }}
                  >
                    {selectedModule.title}
                  </button>{" "}
                  · {selectedModule.duration}
                </p>
              </>
            ) : (
              <>
                <p style={{ fontSize: 14.5, opacity: 0.8, lineHeight: 1.6, marginBottom: 20 }}>{selectedModule.description}</p>
                {(selectedModule.subtopics || []).length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <p className="sp-mono" style={{ fontSize: 10.5, opacity: 0.55, marginBottom: 8 }}>WHAT'S INSIDE THIS STEP</p>
                    <div className="flex flex-col" style={{ gap: 6 }}>
                      {selectedModule.subtopics.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => setSelectedSub(s)}
                          className="rs-sub"
                          style={{ maxWidth: "none", width: "100%" }}
                        >
                          {s.title}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            <div className="flex flex-col" style={{ gap: 10, marginBottom: 24 }}>
              <button
                onClick={() => {
                  setVideoFocus(selectedModule.id);
                  setView("videos");
                  closePanel();
                  requestAnimationFrame(() => roadmapRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
                }}
                className="sp-link-btn flex items-center gap-1.5"
                style={{ borderRadius: 10, padding: "10px 14px", fontSize: 13.5, cursor: "pointer", background: "transparent", textAlign: "left" }}
              >
                <PlayCircle size={16} style={{ flexShrink: 0 }} />
                <span>See free videos for this step</span>
                <ArrowRight size={13} style={{ opacity: 0.5, marginLeft: "auto", flexShrink: 0 }} />
              </button>
              <a
                className="sp-link-btn flex items-center gap-1.5"
                href={selectedModule.certUrl}
                target="_blank" rel="noopener noreferrer"
                style={{ borderRadius: 10, padding: "10px 14px", fontSize: 13.5, textDecoration: "none" }}
              >
                <Award size={16} style={{ flexShrink: 0 }} />
                <span>{selectedModule.certLabel}</span>
                <ExternalLink size={12} style={{ opacity: 0.5, marginLeft: "auto", flexShrink: 0 }} />
              </a>
            </div>

            <div style={{ borderTop: "1px solid var(--line)", paddingTop: 18 }}>
              {(() => {
                const m = selectedModule;
                const r = results[m.id];
                const n = m.questionCount || 0;
                const need = Math.ceil(n * 0.7);
                if (completed[m.id]) {
                  return (
                    <div className="flex items-center flex-wrap" style={{ gap: 14 }}>
                      <span className="flex items-center gap-1.5" style={{ color: "var(--teal)", fontWeight: 700, fontSize: 14.5 }}>
                        <CheckCircle2 size={18} /> Step reached{r ? ` · best ${r.best}/${r.total}` : ""}
                      </span>
                      {n > 0 && (
                        <button onClick={() => openAssessment(m)} className="sp-link-btn" style={{ borderRadius: 10, padding: "7px 14px", fontSize: 13, cursor: "pointer", background: "transparent" }}>
                          Retake assessment
                        </button>
                      )}
                    </div>
                  );
                }
                if (n === 0) return <p style={{ fontSize: 13, opacity: 0.65 }}>An assessment for this step is coming soon.</p>;
                return (
                  <div>
                    <button onClick={() => openAssessment(m)} className="sp-btn-blaze flex items-center gap-1.5" style={{ border: "none", borderRadius: 10, padding: "10px 20px", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>
                      <Circle size={16} /> Mark as reached
                    </button>
                    <p style={{ fontSize: 12.5, opacity: 0.65, marginTop: 8, lineHeight: 1.5 }}>
                      Marking a step as reached starts a {n}-question check on this topic. Pass with {need} or more.
                      {r ? ` Best so far: ${r.best}/${r.total}.` : ""}
                    </p>
                  </div>
                );
              })()}

              <button
                onClick={() => toggleBookmark(selectedModule.id)}
                className="sp-icon-btn flex items-center gap-1.5"
                style={{ marginTop: 16, border: "none", background: "transparent", cursor: "pointer", fontSize: 13.5, color: bookmarked[selectedModule.id] ? "var(--blaze)" : "var(--ink)", opacity: bookmarked[selectedModule.id] ? 1 : 0.55, fontWeight: 600, padding: 0 }}
              >
                <Flag size={16} fill={bookmarked[selectedModule.id] ? "var(--blaze)" : "none"} />
                {bookmarked[selectedModule.id] ? "Bookmarked" : "Bookmark this step"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------------- PROGRESS & CERTIFICATES ---------------- */}
      <MyProgress
        user={user}
        roadmaps={roadmaps}
        results={results}
        certificates={certificates}
        onSignIn={() => { setAuthNotice(""); setAuthMode("login"); setShowLogin(true); }}
        onOpenSkill={goToSkill}
        onOpenCertificate={setCertView}
      />

      {/* ---------------- BOOKMARKS ---------------- */}
      <section style={{ maxWidth: 900, margin: "0 auto", padding: "56px 20px" }}>
        <p className="sp-mono sp-text-teal" style={{ fontSize: 12 }}>YOUR STOPS</p>
        <h2 className="sp-display" style={{ fontSize: 24, fontWeight: 600, marginTop: 6, marginBottom: 20 }}>
          Bookmarked resources
        </h2>
        {bookmarkList.length === 0 ? (
          <p style={{ fontSize: 14.5, opacity: 0.65 }}>
            No stops bookmarked yet — tap the flag icon on any roadmap step to save it here.
          </p>
        ) : (
          <div className="flex flex-col" style={{ gap: 10 }}>
            {bookmarkList.map(({ key, skillName, module }) => (
              <button
                key={`${key}:${module.id}`}
                onClick={() => goToSkill(key)}
                className="sp-card flex items-center justify-between"
                style={{ width: "100%", textAlign: "left", borderRadius: 10, padding: "12px 16px", cursor: "pointer" }}
              >
                <span>
                  <span style={{ fontWeight: 600, fontSize: 14.5 }}>{module.title}</span>
                  <span style={{ opacity: 0.6, fontSize: 13 }}> · {skillName}</span>
                </span>
                <ArrowRight size={15} className="sp-text-teal" />
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ---------------- CERTIFICATION PROVIDERS ---------------- */}
      <section id="certs" className="sp-bg-card" style={{ borderTop: "1px solid var(--line)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "64px 20px" }}>
          <p className="sp-mono sp-text-teal" style={{ fontSize: 12 }}>CERTIFICATION TRAILHEAD</p>
          <h2 className="sp-display" style={{ fontSize: 28, fontWeight: 600, marginTop: 6, marginBottom: 32 }}>
            Free certificate providers we pull from
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 16 }}>
            {PROVIDERS.map((p) => (
              <a
                key={p.name}
                href={p.url}
                target="_blank" rel="noopener noreferrer"
                className="sp-link-btn"
                style={{ display: "block", borderRadius: 12, padding: "16px 18px", textDecoration: "none" }}
              >
                <div className="flex items-center justify-between">
                  <span style={{ fontWeight: 600, fontSize: 15 }}>{p.name}</span>
                  <ExternalLink size={13} style={{ opacity: 0.5 }} />
                </div>
                <p style={{ fontSize: 13, opacity: 0.7, marginTop: 6, lineHeight: 1.5 }}>{p.note}</p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- FOOTER ---------------- */}
      <footer className="sp-bg-forest">
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "36px 20px" }} className="flex flex-wrap items-center justify-between" >
          <div className="flex items-center gap-2">
            <Compass size={18} className="sp-text-blaze" />
            <span className="sp-display sp-text-paper" style={{ fontSize: 16, fontWeight: 600 }}>SkillPath</span>
          </div>
          <p className="sp-text-paper" style={{ opacity: 0.55, fontSize: 12.5 }}>
            Mini Project · MCA Semester 1 · KTU — built by Ali
          </p>
        </div>
      </footer>

      {/* ---------------- ADMIN CONSOLE (admins only) ---------------- */}
      {showAdmin && user && user.role === "admin" && (
        <AdminConsole user={user} roadmaps={roadmaps} reloadContent={reloadContent} onClose={() => setShowAdmin(false)} />
      )}

      {/* ---------------- ASSESSMENT + CERTIFICATE OVERLAYS ---------------- */}
      {assessment && (
        <AssessmentModal
          st={assessment}
          onClose={() => setAssessment(null)}
          setAnswer={setAssessmentAnswer}
          goTo={(i) => setAssessment((p) => (p && p.data ? { ...p, current: Math.max(0, Math.min(i, p.data.questions.length - 1)) } : p))}
          submit={submitAssessment}
          retake={retakeAssessment}
          openCertificate={(c) => { setAssessment(null); setCertView(c); }}
        />
      )}
      {certView && <CertificateView cert={certView} onClose={() => setCertView(null)} />}

      {/* ---------------- LOGIN MODAL ---------------- */}
      {showLogin && (
        <div
          onClick={() => setShowLogin(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(18,36,28,0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 70, padding: 20 }}
        >
          <div onClick={(e) => e.stopPropagation()} className="sp-bg-card sp-fade-in" style={{ borderRadius: 16, padding: 28, width: "100%", maxWidth: 360, border: "1px solid var(--line)" }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
              <h3 className="sp-display" style={{ fontSize: 20, fontWeight: 600 }}>
                {authMode === "login" ? "Sign in" : "Create your account"}
              </h3>
              <button onClick={() => setShowLogin(false)} className="sp-icon-btn" style={{ border: "none", background: "transparent", cursor: "pointer" }} aria-label="Close">
                <X size={18} />
              </button>
            </div>

            {authNotice && (
              <p style={{ fontSize: 12.5, color: "var(--teal)", marginBottom: 14 }}>{authNotice}</p>
            )}

            <form onSubmit={handleAuthSubmit}>
              {authMode === "register" && (
                <>
                  <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>Your name</label>
                  <input
                    autoFocus
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    placeholder="e.g. Ali"
                    className="sp-input"
                    style={{ width: "100%", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 12px", fontSize: 14, marginBottom: 14, background: "var(--paper)" }}
                  />
                </>
              )}

              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>Email</label>
              <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                placeholder="you@example.com"
                className="sp-input"
                style={{ width: "100%", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 12px", fontSize: 14, marginBottom: 14, background: "var(--paper)" }}
              />

              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>Password</label>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder={authMode === "register" ? "6+ characters" : "••••••••"}
                className="sp-input"
                style={{ width: "100%", border: "1px solid var(--line)", borderRadius: 8, padding: "10px 12px", fontSize: 14, marginBottom: 8, background: "var(--paper)" }}
              />

              {authError && (
                <p style={{ fontSize: 12.5, color: "#C0503E", marginBottom: 10 }}>{authError}</p>
              )}

              <button type="submit" className="sp-btn-blaze" style={{ width: "100%", border: "none", borderRadius: 8, padding: "10px", fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 8 }}>
                {authMode === "login" ? "Sign in" : "Create account"}
              </button>
            </form>

            <p style={{ fontSize: 12.5, opacity: 0.7, marginTop: 14, textAlign: "center" }}>
              {authMode === "login" ? (
                <>New here? <button onClick={() => { setAuthMode("register"); setAuthError(""); }} className="sp-icon-btn" style={{ border: "none", background: "none", color: "var(--teal)", fontWeight: 600, cursor: "pointer", padding: 0 }}>Create an account</button></>
              ) : (
                <>Already have one? <button onClick={() => { setAuthMode("login"); setAuthError(""); }} className="sp-icon-btn" style={{ border: "none", background: "none", color: "var(--teal)", fontWeight: 600, cursor: "pointer", padding: 0 }}>Sign in</button></>
              )}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

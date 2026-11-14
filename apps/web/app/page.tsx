"use client";
import {useState} from "react";
import {QueryClient,QueryClientProvider,useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {Button} from "@/components/ui/button";
import {PlanTree} from "@/components/plan";
import {BenchmarkChart} from "@/components/benchmarks";
import type {Candidate,Session,Workload} from "@/lib/types";

async function request<T>(path:string,token:string,body?:unknown):Promise<T> {
 const response=await fetch(`/api/${path}`,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const result=await response.json();
 if(!response.ok) throw new Error(typeof result.detail==="string"?result.detail:result.error||`API request failed (${response.status})`);
 return result as T;
}
function CandidateView({candidate,original}:{candidate:Candidate;original?:string}) {
 const b=candidate.benchmark;
 return <article className="candidate"><div className="section-heading"><h3>Candidate {candidate.id.slice(0,8)}</h3><span className={candidate.accepted?"status accepted":"status"}>{candidate.accepted?"Accepted":"Rejected"}</span></div>
 <p>{candidate.hypothesis}</p><p className="muted">Source: {candidate.source} | Equivalence: {candidate.validation?.status||"not validated"}</p>
 <pre><code>{candidate.sql}</code></pre>{candidate.index!=null&&<details><summary>Index proposal</summary><pre>{JSON.stringify(candidate.index,null,2)}</pre></details>}
 {candidate.validation&&<p>{candidate.validation.reason}</p>}{candidate.rejection_reasons?.map(r=><p className="failure" key={r}>{r}</p>)}{candidate.error&&<p role="alert" className="failure">Execution error: {candidate.error}</p>}
 <details><summary>Assumptions</summary><ul>{candidate.assumptions.map(a=><li key={a}>{a}</li>)}</ul></details>
 {b&&<><dl className="measurements"><div><dt>Median speedup</dt><dd>{b.median_speedup.toFixed(2)}x</dd></div><div><dt>Baseline median</dt><dd>{b.baseline.median_ms.toFixed(3)} ms</dd></div><div><dt>Candidate median</dt><dd>{b.candidate.median_ms.toFixed(3)} ms</dd></div><div><dt>95% bootstrap interval</dt><dd>{b.speedup_ci95.map(n=>n.toFixed(2)).join(" to ")}x</dd></div><div><dt>Index storage</dt><dd>{b.index_bytes.toLocaleString()} bytes</dd></div></dl>
 <BenchmarkChart benchmark={b}/><div className="split"><section><h4>Baseline plan</h4><PlanTree node={b.plans.baseline.Plan}/></section><section><h4>Candidate plan</h4><PlanTree node={b.plans.candidate.Plan}/></section></div><details><summary>Machine-readable plan differences</summary><pre>{JSON.stringify(b.plan_difference,null,2)}</pre></details></>}
 {original&&candidate.sql===original&&<p className="muted">SQL text is unchanged. This candidate tests physical index design.</p>}</article>;
}
function Workspace() {
 const cache=useQueryClient();
 const [token,setToken]=useState("");
 const [sql,setSql]=useState("");
 const [workload,setWorkload]=useState("");
 const [selected,setSelected]=useState<string|null>(null);
 const [provider,setProvider]=useState("deterministic");
 const workloads=useQuery({queryKey:["workloads",token],queryFn:()=>request<Workload[]>("workloads",token)});
 const sessions=useQuery({queryKey:["sessions",token],queryFn:()=>request<Session[]>("optimizations?limit=100",token),refetchInterval:2500});
 const totals=useQuery({queryKey:["summary",token],queryFn:()=>request<{total:number;completed:number;improved:number;unchanged:number;coverage:number}>("summary",token),refetchInterval:2500});
 const session=useQuery({queryKey:["session",selected,token],queryFn:()=>request<Session>(`optimizations/${selected}`,token),enabled:!!selected,refetchInterval:q=>["queued","running"].includes(q.state.data?.status||"")?1500:false});
 const submit=useMutation({mutationFn:()=>request<{id:string}>("optimizations",token,{sql,provider,workload_id:workload||null}),onSuccess:result=>{setSelected(result.id);cache.invalidateQueries({queryKey:["sessions"]});}});
 const cancel=useMutation({mutationFn:()=>request(`optimizations/${selected}/cancel`,token,{}),onSuccess:()=>cache.invalidateQueries({queryKey:["session",selected]})});
 const current=session.data;
 const report=current?.report;
 const error=submit.error||sessions.error||workloads.error||session.error||totals.error||cancel.error;
 const exportReport=()=>{if(!current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:"application/json"}));const anchor=document.createElement("a");anchor.href=url;anchor.download=`optimization-${current.id}.json`;anchor.click();URL.revokeObjectURL(url);};
 return <div className="application"><aside><a className="brand" href="/">Postgres<br/><strong>Query Engineer</strong></a><nav aria-label="Main navigation"><a href="#workspace">SQL workspace</a><a href="#activity">Optimization sessions</a><a href="#evidence">Experiment evidence</a></nav><div className="boundary"><strong>Controlled experiments</strong><p>Local benchmark database. Recommendations require measured evidence.</p></div></aside>
 <main><header><div><h1>Query performance</h1><p className="muted">Inspect plans. Validate semantics. Measure candidates.</p></div><label className="access">API access token<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off" placeholder="Optional for local deployment"/></label></header>
 {error&&<div role="alert" className="error">{error.message}</div>}
 <dl className="overview"><div><dt>Total sessions</dt><dd>{totals.data?.total??"Unavailable"}</dd></div><div><dt>Completed</dt><dd>{totals.data?.completed??"Unavailable"}</dd></div><div><dt>Validated improvements</dt><dd>{totals.data?.improved??"Unavailable"}</dd></div><div><dt>No accepted improvement</dt><dd>{totals.data?.unchanged??"Unavailable"}</dd></div><div><dt>Workloads evaluated</dt><dd>{totals.data?`${totals.data.coverage} / ${workloads.data?.length??12}`:"Unavailable"}</dd></div></dl>
 <section id="workspace" className="workspace"><div className="section-heading"><h2>SQL workspace</h2><span className="muted">SELECT only / commerce schema</span></div><form onSubmit={e=>{e.preventDefault();submit.mutate();}}><div className="controls"><label>Workload<select value={workload} onChange={e=>{setWorkload(e.target.value);setSql(workloads.data?.find(w=>w.id===e.target.value)?.sql||"");}}><option value="">Custom query</option>{workloads.data?.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label><label>Candidate provider<select value={provider} onChange={e=>setProvider(e.target.value)}><option value="deterministic">Deterministic</option><option value="openai">OpenAI compatible</option></select></label></div>
 <label htmlFor="sql">PostgreSQL query</label><textarea id="sql" spellCheck={false} value={sql} maxLength={20000} onChange={e=>{setSql(e.target.value);setWorkload("");}} placeholder="Select a workload or enter a SELECT query" required/>
 <div className="section-heading"><p className="muted">Up to 8 candidates. Exact finite comparisons precede benchmarking.</p><Button type="submit" disabled={!sql.trim()||submit.isPending}>{submit.isPending?"Submitting...":"Run optimization"}</Button></div></form></section>
 <section id="activity"><h2>Optimization sessions</h2>{sessions.isLoading&&<p role="status">Loading sessions...</p>}{sessions.data?.length===0&&<p className="empty">No sessions recorded. Submit a query to start an experiment.</p>}
 <div className="table-scroll"><table><caption>Most recent 100 sessions</caption><thead><tr><th>Session</th><th>Workload</th><th>Status</th><th>Created</th></tr></thead><tbody>{sessions.data?.map(s=><tr key={s.id} className={s.id===selected?"selected":""}><td><button className="link" onClick={()=>setSelected(s.id)}>{s.id.slice(0,8)}</button></td><td>{s.request.workload_id||"Custom query"}</td><td>{s.status}</td><td>{new Date(s.created_at).toLocaleString()}</td></tr>)}</tbody></table></div></section>
 <section id="evidence"><div className="section-heading"><h2>Experiment evidence</h2>{current&&<div className="actions"><Button variant="secondary" onClick={exportReport}>Export JSON report</Button>{["queued","running"].includes(current.status)&&<Button variant="secondary" disabled={cancel.isPending} onClick={()=>cancel.mutate()}>Cancel session</Button>}</div>}</div>
 {!selected&&<p className="empty">Select a session to inspect plans, candidate validation and measurements.</p>}{session.isLoading&&selected&&<p role="status">Loading experiment...</p>}
 {current&&<><p role="status">Session {current.id} | {current.status}</p>{report?.error&&<p role="alert" className="failure">{report.error}</p>}
 <details open><summary>Original SQL</summary><pre><code>{current.request.sql}</code></pre></details>
 {report?.decision&&<section className="recommendation"><h3>{report.decision==="validated_improvement"?"Measured improvement accepted":"Original query retained"}</h3><pre><code>{report.recommended_sql}</code></pre><p>Acceptance reflects the configured correctness, variance, storage and regression gates.</p></section>}
 {report?.diagnostics?.length===0&&<p>No deterministic plan warnings were detected.</p>}{report?.diagnostics?.map((d,i)=><p key={i}><strong>{d.code}</strong> | node {d.path}: {d.message}</p>)}
 {report?.baseline_plan&&<details><summary>Original execution plan</summary><PlanTree node={report.baseline_plan.Plan}/></details>}
 {report?.candidates?.map(c=><CandidateView key={c.id} candidate={c} original={current.request.sql}/>)}
 <details open><summary>Tool execution history</summary><ol className="events">{current.events.map((e,i)=><li key={i}><time>{new Date(e.at).toLocaleTimeString()}</time><strong>{e.stage}</strong><span>{e.status||"recorded"}</span><span>{e.duration_seconds?.toFixed(3)}{e.duration_seconds!==undefined?" s":""}</span></li>)}</ol>{current.events.length===0&&<p>Waiting for the worker to claim this session.</p>}</details>
 {report?.policy&&<details><summary>Acceptance policy and model usage</summary><pre>{JSON.stringify({policy:report.policy,model_usage:report.model_usage},null,2)}</pre></details>}{report?.limitations&&<ul className="muted">{report.limitations.map(l=><li key={l}>{l}</li>)}</ul>}</>}
 </section></main></div>;
}
export default function Page(){const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:false}}}));return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>;}

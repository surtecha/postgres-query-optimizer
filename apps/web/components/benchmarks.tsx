"use client";
import {Bar,BarChart,CartesianGrid,Legend,ResponsiveContainer,Tooltip,XAxis,YAxis} from "recharts";
import type {Benchmark} from "@/lib/types";
export function BenchmarkChart({benchmark}:{benchmark:Benchmark}) {
 const data=benchmark.runs.filter(r=>r.label==="baseline").map(r=>({trial:r.trial+1,baseline:r.latency_ms,candidate:benchmark.runs.find(c=>c.label==="candidate"&&c.trial===r.trial)?.latency_ms}));
 return <><div className="chart" role="img" aria-label="Paired baseline and candidate execution latency in milliseconds"><ResponsiveContainer width="100%" height={240}><BarChart data={data}><CartesianGrid stroke="#303946" vertical={false}/><XAxis dataKey="trial" stroke="#a4b1c1"/><YAxis stroke="#a4b1c1" unit=" ms"/><Tooltip/><Legend/><Bar dataKey="baseline" fill="#8398b4" isAnimationActive={false}/><Bar dataKey="candidate" fill="#72d5bb" isAnimationActive={false}/></BarChart></ResponsiveContainer></div>
 <div className="table-scroll" role="region" aria-label="Paired trial measurements" tabIndex={0}><table><caption>Measured paired trials</caption><thead><tr><th>Trial</th><th>Variant</th><th>Latency, ms</th><th>Hit blocks</th><th>Read blocks</th></tr></thead><tbody>{benchmark.runs.map(r=><tr key={`${r.trial}-${r.label}`}><td>{r.trial+1}</td><td>{r.label}</td><td>{r.latency_ms.toFixed(3)}</td><td>{r.buffer_hits}</td><td>{r.buffer_reads}</td></tr>)}</tbody></table></div></>;
}

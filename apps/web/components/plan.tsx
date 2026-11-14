import type { Plan } from "@/lib/types";
export function PlanTree({node,depth=0}:{node:Plan;depth?:number}) {
 return <div className="plan-node"><details open={depth<3}><summary><strong>{node["Node Type"] || "Unknown operator"}</strong> <span>{node["Actual Total Time"]?.toFixed(3) ?? "?"} ms</span></summary>
 <dl className="plan-stats"><div><dt>Estimated rows</dt><dd>{node["Plan Rows"] ?? "?"}</dd></div><div><dt>Actual rows / loop</dt><dd>{node["Actual Rows"] ?? "?"}</dd></div><div><dt>Loops</dt><dd>{node["Actual Loops"] ?? "?"}</dd></div><div><dt>Hit / read blocks</dt><dd>{node["Shared Hit Blocks"] ?? 0} / {node["Shared Read Blocks"] ?? 0}</dd></div></dl>
 {node["Index Name"] && <code>{node["Index Name"]}</code>}{node["Sort Method"] && <p>Sort: {node["Sort Method"]}</p>}
 {(node.Plans||[]).map((child,i)=><PlanTree key={i} node={child} depth={depth+1}/>)}</details></div>;
}

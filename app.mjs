import { filterMethods, filterDatasets, sortRows, csvText } from "./table-tools.mjs";

const $ = (id) => document.getElementById(id);
const el = (tag, value, className) => {
  const node = document.createElement(tag);
  if (value != null) node.textContent = value;
  if (className) node.className = className;
  return node;
};
const link = (url, title) => {
  const node = el("a", title);
  node.href = url;
  node.rel = "noopener noreferrer";
  node.target = "_blank";
  return node;
};
const cell = (row, value, css) => {
  const td = el("td", typeof value === "string" ? value : null, css);
  if (value instanceof Node) td.append(value);
  row.append(td);
  return td;
};
const selectOptions = (select, pairs, placeholder) => {
  const entries = placeholder ? [["", placeholder], ...pairs] : pairs;
  select.replaceChildren(...entries.map(([value, label]) => {
    const option = el("option", label);
    option.value = value;
    return option;
  }));
};
const uniquePairs = (values) => [...new Set(values)].sort().map(v => [v, v]);
const pressed = (button, value) => button.setAttribute("aria-pressed", String(value));
const fade = (node) => node.animate?.([{opacity:.57, transform:"translateY(4px)"}, {opacity:1, transform:"translateY(0)"}], {duration:250,easing:"ease-out"});
const typeName = {
  I: ["View-indexed", "#2f6f96"], II: ["Spatial query", "#a3543c"],
  III: ["Regular grid", "#527087"], IV: ["Irregular set", "#756047"],
};
const tag = (code) => el("span", code + " · " + typeName[code][0], "kind tone-" + code.toLowerCase());
const citeLink = (number) => {
  const node = el("a", "[" + number + "]", "cite-marker");
  node.href = "references.html#ref-" + number;
  node.setAttribute("aria-label", "Reference " + number);
  return node;
};

function pageTable(prefix, limit, list, render) {
  let page = 0;
  const prev = $(prefix + "-prev"), next = $(prefix + "-next"), body = $(prefix + "-rows");
  function draw(animate = false) {
    const data = list(), count = Math.ceil(data.length / limit);
    page = Math.max(0, Math.min(page, count - 1));
    body.replaceChildren(...data.slice(page * limit, (page + 1) * limit).map(render));
    if (!data.length) {
      const row = el("tr");
      cell(row, "No matches. Try a different search or filter.").colSpan = 4;
      body.append(row);
    }
    const span = data.length ? "Showing " + (page * limit + 1) + "–" +
      Math.min((page + 1) * limit, data.length) + " of " + data.length : "No matching entries";
    $(prefix + "-count").textContent = span;
    prev.disabled = page === 0;
    next.disabled = page + 1 >= count;
    if (animate) fade(body);
  }
  prev.addEventListener("click", () => { page--; draw(true); });
  next.addEventListener("click", () => { page++; draw(true); });
  draw();
  return () => { page = 0; draw(true); };
}

function methodsIndex(data) {
  const query = $("method-query");
  const buttons = [...$("method-types").querySelectorAll("button")];
  let mechanism = "";
  const reset = pageTable("method", 10, () => filterMethods(data, {query:query.value, mechanism}), (r) => {
    const row = el("tr");
    cell(row, r.name).append(citeLink(r.reference_number),
      el("span", [r.venue, r.year].filter(Boolean).join(" · "), "cell-secondary"));
    cell(row, tag(r.mechanism));
    cell(row, r.settings.join(" / "));
    const links = cell(row);
    if (r.paper) links.append(link(r.paper, "Paper"));
    if (r.source && r.source !== r.paper) {
      links.append(link(r.source, /^https?:\/\/(github\.com|gitlab\.com)\//i.test(r.source) ? "Code" : "Author resource"));
    }
    if (!links.childNodes.length) links.textContent = "NA";
    return row;
  });
  function setType(value) {
    mechanism = value;
    buttons.forEach(button => pressed(button, button.dataset.mechanism === value));
    reset();
  }
  query.addEventListener("input", reset);
  buttons.forEach(button => button.addEventListener("click", () => setType(button.dataset.mechanism)));
  document.querySelectorAll("[data-jump]").forEach(node => node.addEventListener("click", () => {
    query.value = "";
    setType(node.dataset.jump);
  }));
  const chosen = new URLSearchParams(location.search).get("mechanism");
  if (Object.hasOwn(typeName, chosen)) setType(chosen);
}

function datasetIndex(data) {
  const query = $("dataset-query"), task = $("dataset-task"), proj = $("dataset-projection");
  selectOptions(task, uniquePairs(data.map(d => d.domain)), "All tasks");
  selectOptions(proj, uniquePairs(data.flatMap(d => d.projection)), "All observations");
  const reset = pageTable("dataset", 9, () => filterDatasets(data, {
    query:query.value, scene:task.value, projection:proj.value,
  }), (r) => {
    const row = el("tr");
    cell(row, r.paper ? link(r.paper, r.name) : r.name).append(
      ...r.reference_numbers.map(citeLink), el("span", r.domain, "cell-secondary"));
    cell(row, r.scale); cell(row, r.observations); cell(row, r.reference);
    return row;
  });
  query.addEventListener("input", reset);
  [task, proj].forEach(node => node.addEventListener("change", reset));
}

const FIRST_GROUP = {
  DTU:"G:calibrated", RealEstate10K:"N6", ScanNet:"A3", Matterport3D:"P-NVS:native_erp",
};
const METRIC = {
  overall_mm:["Overall (mm)",1,3], accuracy_mm:["Accuracy (mm)",1,3],
  completeness_mm:["Completeness (mm)",1,3],
  fscore_05m:["F-score@5 cm (%)",100,1,true], auc_at_30_pct:["AUC@30° (%)",1,1,true],
  accuracy_m:["Accuracy (m)",1,3], completeness_m:["Completeness (m)",1,3],
  rotation_deg:["Rotation error (°)",1,2], translation_deg:["Translation direction error (°)",1,2],
  psnr_db:["PSNR (dB)",1,2,true], ws_psnr_db:["WS-PSNR (dB)",1,2,true],
  ssim:["SSIM",1,3,true], lpips:["LPIPS",1,3],
  fusion_fscore_05m:["Fused F-score@5 cm (%)",100,1,true],
  fusion_accuracy_m:["Fused accuracy (m)",1,3], fusion_completeness_m:["Fused completeness (m)",1,3],
  depth_baseline_absrel:["Depth AbsRel",1,3], depth_baseline_mae_m:["Depth MAE (m)",1,3],
  median_total:["Total time (s)",1,3], max_peak_allocated_gib:["Peak GPU memory (GiB)",1,2],
  system_params:["System parameters (M)",1e-6,2], gaussian_count:["Gaussians (K)",1e-3,1],
  median_depth_prior_generation_s:["Depth prior time (s)",1,3],
};
const NOT_QUALITY = new Set(["median_total","max_peak_allocated_gib","system_params","gaussian_count","median_depth_prior_generation_s"]);
const PERCENT_METRICS = new Set(["fscore_05m", "fusion_fscore_05m", "auc_at_30_pct"]);
const valueAt = (row, key) => Number.isFinite(row[key]) ? row[key] * METRIC[key][1] : null;
const formatValue = (row, key) => valueAt(row, key)?.toFixed(METRIC[key][2]) ?? "NA";

function makeScatter(canvas, tip) {
  let marks = [];
  canvas.addEventListener("pointerleave", () => { tip.hidden = true; });
  canvas.addEventListener("pointermove", e => {
    const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    const point = marks.map(mark => [mark, (mark.x-x)**2+(mark.y-y)**2])
      .filter(([,d]) => d < 108).sort((a,b) => a[1]-b[1])[0]?.[0];
    tip.hidden = !point;
    if (!point) return;
    tip.textContent = point.text;
    tip.style.left = Math.max(5, Math.min(x+10,r.width-229)) + "px";
    tip.style.top = Math.max(3,y-63) + "px";
  });
  function limits(values) {
    const lo = Math.min(...values), hi = Math.max(...values);
    const margin = hi === lo ? Math.max(.03, Math.abs(hi)*.08) : (hi-lo)*.10;
    return [lo-margin, hi+margin];
  }
  const tick = (v) => Number(v.toPrecision(3)).toString();
  return (rows, cost, score, hidden) => {
    marks = [];
    tip.hidden = true;
    const w = canvas.clientWidth, h = canvas.clientHeight, ratio = devicePixelRatio || 1;
    if (!w || !h || !score) return;
    canvas.width = Math.round(w*ratio); canvas.height = Math.round(h*ratio);
    const c = canvas.getContext("2d");
    c.scale(ratio,ratio);
    const points = rows.map(r => ({row:r,x:valueAt(r,cost),y:valueAt(r,score)}))
      .filter(p => p.x != null && p.y != null);
    if (!points.length) return;
    const left = 53, right = w-18, top = 29, bottom = h-45;
    const xs = points.map(p=>p.x);
    const log = cost === "median_total" && Math.min(...xs)>0 && Math.max(...xs)/Math.min(...xs)>25;
    const conv = (v)=>log ? Math.log10(v) : v;
    const [a,b] = limits(xs.map(conv));
    const [lower, upper] = limits(points.map(p=>p.y));
    const [d,e] = PERCENT_METRICS.has(score)
      ? [Math.max(0, lower), Math.min(100, upper)]
      : [lower, upper];
    const xp = (x)=>left+(right-left)*(conv(x)-a)/(b-a);
    const yp = (y)=>bottom-(bottom-top)*(y-d)/(e-d);
    const line = (x0,y0,x1,y1) => { c.beginPath(); c.moveTo(x0,y0); c.lineTo(x1,y1); c.stroke(); };
    c.font = "12px \"Segoe UI\", system-ui"; c.fillStyle = "#5b6861"; c.strokeStyle = "#dfe6e1";
    c.textAlign = "left"; c.textBaseline = "middle";
    c.fillText(METRIC[score][0],left,11);
    c.textAlign = "right"; c.textBaseline = "middle";
    for(let i=0;i<=4;i++) {
      const value=d+(e-d)*i/4, y=yp(value);
      line(left,y,right,y); c.fillText(tick(value),left-6,y);
    }
    c.strokeStyle="#87958c"; line(left,top,left,bottom); line(left,bottom,right,bottom);
    c.textAlign="center";
    const n = w<420 ? 3 : 4;
    for(let i=0;i<=n;i++) {
      const raw=a+(b-a)*i/n;
      c.fillText(tick(log?10**raw:raw),left+(right-left)*i/n,bottom+12);
    }
    c.fillText(METRIC[cost][0]+(log ? " · log scale":""),
      (left+right)/2,h-10);
    for(const p of points) {
      const r = p.row;
      if(hidden.has(r.mechanism)) continue;
      const x=xp(p.x), y=yp(p.y);
      c.beginPath(); c.arc(x,y,5.4,0,2*Math.PI); c.fillStyle=typeName[r.mechanism][1]; c.fill();
      c.strokeStyle="#fff"; c.stroke();
      marks.push({x,y,text:r.name+"\n"+METRIC[score][0]+": "+formatValue(r,score)+
        "\n"+METRIC[cost][0]+": "+formatValue(r,cost)});
    }
    const description=METRIC[score][0]+" versus "+METRIC[cost][0]+(log?" on a logarithmic cost axis.":".");
    canvas.setAttribute("aria-label",description);
    $("chart-description").textContent=marks.length ? description+" Exact values appear below."
      : "Enable a mechanism available in this setup to show its points. Exact values appear below.";
  };
}

function resultsExplorer(data) {
  const tabs=[...$("result-tabs").querySelectorAll("button")];
  const setup=$("result-setup"), score=$("result-quality"), cost=$("result-cost");
  const canvas=$("scatter"), plot=makeScatter(canvas,$("chart-tip"));
  const hidden=new Set();
  let dataset="DTU", current=[], ordered=[], metrics=[], sortKey="", direction="";
  const legend=[...document.querySelectorAll(".chart-key li")].map((li,i)=>{
    const key=Object.keys(typeName)[i], btn=el("button",null,"legend-toggle");
    btn.type="button"; btn.append(...li.childNodes); li.replaceChildren(btn); pressed(btn,true);
    btn.addEventListener("click",()=>{
      if(hidden.has(key)) hidden.delete(key); else hidden.add(key);
      pressed(btn,!hidden.has(key)); redraw(true);
    });
    return btn;
  });
  function redraw(animate=false) {
    plot(current,cost.value,score.value,hidden);
    if(animate) fade(canvas);
  }
  function chooseDataset(name, animate=false) {
    dataset=name;
    tabs.forEach(t=>pressed(t,t.dataset.dataset===name));
    selectOptions(setup,[...new Map(data.filter(r=>r.dataset===dataset).map(r=>[r.group,r.setup]))]);
    if([...setup.options].some(o=>o.value===FIRST_GROUP[dataset])) setup.value=FIRST_GROUP[dataset];
    chooseSetup(animate);
  }
  function chooseSetup(animate=true) {
    current=data.filter(r=>r.dataset===dataset && r.group===setup.value);
    metrics=Object.keys(METRIC).filter(k=>current.some(r=>Number.isFinite(r[k])));
    const quality=metrics.filter(k=>!NOT_QUALITY.has(k));
    selectOptions(score,quality.map(k=>[k,METRIC[k][0]]));
    sortKey=quality[0] || "name";
    direction=METRIC[sortKey]?.[3]?"desc":"asc";
    hidden.clear(); legend.forEach(b=>pressed(b,true));
    const r=current[0];
    $("result-meta").textContent=r ? [
      current.length+" configurations",r.samples+" valid samples per configuration",
      r.views+" input views",r.targets?r.targets+" target views":"",
    ].filter(Boolean).join(" · "):"No measurements for this setup.";
    $("result-note").textContent=setup.value==="P-NVS:native_erp"
      ? "CylinderSplat uses a precomputed depth prior. Its generation time is measured separately."
      : "Legend buttons toggle mechanisms on the chart. The table retains all results in this setup.";
    drawTable(animate); redraw(animate);
  }
  function drawTable(animate=false) {
    const header=el("tr"), spec=[["name","Method"],...metrics.map(k=>[k,METRIC[k][0]])];
    for (const [key,title] of spec) {
      const th=el("th"); th.scope="col";
      if(key===sortKey) th.setAttribute("aria-sort",direction==="asc"?"ascending":"descending");
      const button=el("button",title+(key===sortKey?(direction==="asc"?" ↑":" ↓"):""),"head-sort");
      button.type="button";
      button.addEventListener("click",()=>{
        direction=sortKey===key?(direction==="asc"?"desc":"asc"):(METRIC[key]?.[3]?"desc":"asc");
        sortKey=key; drawTable(true);
        $("result-head").querySelectorAll("button")[spec.findIndex(pair=>pair[0]===key)]?.focus({preventScroll:true});
      });
      th.append(button); header.append(th);
    }
    $("result-head").replaceChildren(header);
    ordered=sortRows(current,sortKey,direction);
    const body=$("result-rows");
    body.replaceChildren(...ordered.map(r=>{
      const row=el("tr");
      cell(row,r.name).append(citeLink(r.reference_number),
        el("span",r.mechanism+" · "+typeName[r.mechanism][0],"cell-secondary"));
      metrics.forEach(k=>cell(row,formatValue(r,k),"numerical"));
      return row;
    }));
    if(animate) fade(body);
  }
  tabs.forEach(t=>t.addEventListener("click",()=>chooseDataset(t.dataset.dataset,true)));
  setup.addEventListener("change",()=>chooseSetup());
  [cost,score].forEach(n=>n.addEventListener("change",()=>redraw(true)));
  new ResizeObserver(()=>redraw()).observe(canvas);
  $("download-current").addEventListener("click",()=>{
    const columns=["name","mechanism","dataset","group","setup","samples"].map(key=>({key,label:key}));
    columns.push(...metrics.map(key=>({key,label:METRIC[key][0]})));
    const rows=ordered.map(r=>{
      const normalized={...r};
      metrics.forEach(k=>{normalized[k]=valueAt(r,k);});
      return normalized;
    });
    const url=URL.createObjectURL(new Blob([csvText(rows,columns)],{type:"text/csv;charset=utf-8"}));
    const a=el("a"); a.href=url; a.download=dataset.toLowerCase()+"-"+setup.value.replaceAll(":","-")+".csv";
    document.body.append(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  const chosen = new URLSearchParams(location.search).get("benchmark");
  chooseDataset(Object.hasOwn(FIRST_GROUP, chosen) ? chosen : "DTU");
}

function motion() {
  if (!("IntersectionObserver" in window)) return;
  const cards = document.querySelectorAll(".section-intro,.mechanism-card,.download-grid article");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("shown");
      observer.unobserve(entry.target);
    });
  }, {threshold:.08});
  cards.forEach(card=>{card.classList.add("reveal"); observer.observe(card);});
}

$("copy-bibtex").addEventListener("click",async()=>{
  try {
    await navigator.clipboard.writeText($("bibtex").innerText.trim());
    $("copy-state").textContent="Copied";
  } catch {
    const sel=window.getSelection(), range=document.createRange();
    range.selectNodeContents($("bibtex")); sel.removeAllRanges(); sel.addRange(range);
    $("copy-state").textContent="Selected for copying";
  }
});
motion();

async function start() {
  const response=await fetch("./data/survey.json");
  if(!response.ok) throw new Error("Could not load site data");
  const data=await response.json();
  for(const id of ["methods","datasets","settings"]) $("count-"+id).textContent=data.counts[id];
  methodsIndex(data.methods);
  datasetIndex(data.datasets);
  resultsExplorer(data.results);
}
start().catch(error=>{
  console.error(error);
  for(const id of ["method-count","dataset-count","result-meta"]) $(id).textContent="Unable to load the interactive data. Use the full CSV downloads.";
});

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import * as d3 from "d3";
import _ from "lodash";

// ─── Color Palette ───
const C = {
  bg: "#0b1120",
  card: "#111827",
  cardAlt: "#1a2332",
  border: "#1e293b",
  accent: "#3b82f6",
  accentLight: "#60a5fa",
  green: "#10b981",
  amber: "#f59e0b",
  red: "#ef4444",
  cyan: "#06b6d4",
  purple: "#8b5cf6",
  pink: "#ec4899",
  white: "#f1f5f9",
  muted: "#94a3b8",
  dimmed: "#64748b",
  tableBg: "#0f172a",
  rowHover: "#1e293b",
  headerBg: "#0284c7",
  headerBg2: "#0e7490",
  weekHeader: "#0891b2",
  weekOrange: "#ea580c",
  weekBlack: "#18181b",
  weekCyan: "#06b6d4",
};

const PIE_COLORS = [
  "#3b82f6","#f97316","#8b5cf6","#ec4899","#eab308","#06b6d4","#10b981","#ef4444","#6366f1","#14b8a6"
];

// ─── Sample Data ───
const SAMPLE_DATA = [
  { "Issue key":"GNOC-11564","Time to Resolution (Minutes)":743,"Summary":"HC : SC - Increase in SMS traffic for PERAX (NSI)","Investigation Type":"Single Customer Issue","Source / Detection":"Health Check","Reporter":"Pranav Doshi","Priority":"P4-Low","Status":"Completed","Assignee":"Pranav Doshi","SLA Status":"Met","Created":"2026-03-07T08:00:00.000+0000","Resolved":"2026-03-07T20:23:00.000+0000" },
  { "Issue key":"GNOC-11582","Time to Resolution (Minutes)":463,"Summary":"HC: Degradation for single Carrier+ customer Sentinel via USA Verizon","Investigation Type":"Single Customer Issue","Source / Detection":"Health Check","Reporter":"Ashay Matekar","Priority":"P4-Low","Status":"Completed","Assignee":"Ashay Matekar","SLA Status":"Met","Created":"2026-03-08T06:00:00.000+0000","Resolved":"2026-03-08T13:43:00.000+0000" },
  { "Issue key":"GNOC-11587","Time to Resolution (Minutes)":258,"Summary":"HC: Increase in RNA for KGS Fire & Security B.V (NSI)","Investigation Type":"Single Customer Issue","Source / Detection":"Alert","Reporter":"Prabhjot Singh","Priority":"P4-Low","Status":"Completed","Assignee":"Prabhjot Singh","SLA Status":"Met","Created":"2026-03-08T10:00:00.000+0000","Resolved":"2026-03-08T14:18:00.000+0000" },
  { "Issue key":"GNOC-11597","Time to Resolution (Minutes)":183,"Summary":"HC: SMS traffic elevated for S.R. Tech(NSI)","Investigation Type":"Single Customer Issue","Source / Detection":"Health Check","Reporter":"Neha Kore","Priority":"P4-Low","Status":"Completed","Assignee":"Neha Kore","SLA Status":"Met","Created":"2026-03-09T04:00:00.000+0000","Resolved":"2026-03-09T07:03:00.000+0000" },
  { "Issue key":"GNOC-11598","Time to Resolution (Minutes)":358,"Summary":"Alert : SC - Shark-tooth pattern in Radius traffc Zenpark (NSI)","Investigation Type":"Single Customer Issue","Source / Detection":"Alert","Reporter":"Pranav Doshi","Priority":"P4-Low","Status":"Completed","Assignee":"Pranav Doshi","SLA Status":"Met","Created":"2026-03-09T05:00:00.000+0000","Resolved":"2026-03-09T10:58:00.000+0000" },
  { "Issue key":"GNOC-11624","Time to Resolution (Minutes)":339,"Summary":"HC: Single Customer- Hafslund Minor Lost Service issue followed by RNA (NSI)","Investigation Type":"Single Customer Issue","Source / Detection":"Alert","Reporter":"Pranav Doshi","Priority":"P4-Low","Status":"Completed","Assignee":"Pranav Doshi","SLA Status":"Met","Created":"2026-03-10T08:00:00.000+0000","Resolved":"2026-03-10T13:39:00.000+0000" },
  { "Issue key":"GNOC-11633","Time to Resolution (Minutes)":1955,"Summary":"Alert: Sparkle System Failure. (CSI)","Investigation Type":"Roaming Sponsor Issue","Source / Detection":"Alert","Reporter":"Ed Guigou","Priority":"P4-Low","Status":"Completed","Assignee":"Ed Guigou","SLA Status":"Met","Created":"2026-03-10T10:00:00.000+0000","Resolved":"2026-03-11T18:35:00.000+0000" },
  { "Issue key":"GNOC-11572","Time to Resolution (Minutes)":1,"Summary":"Temporary unavailability of broker 1 on MSK cluster telco-event-api-prod","Investigation Type":"Monitoring/Tools Issue","Source / Detection":"Alert","Reporter":"Latifa Ouadif","Priority":"P4-Low","Status":"Completed","Assignee":"Latifa Ouadif","SLA Status":"Met","Created":"2026-03-07T14:00:00.000+0000","Resolved":"2026-03-07T14:01:00.000+0000" },
  { "Issue key":"GNOC-11570","Time to Resolution (Minutes)":129,"Summary":"HC: Minor Increase in RNA for SC INVERS GmbH in Orange Belgium (NSI)","Investigation Type":"MNO/VPLMN Issue","Source / Detection":"Health Check","Reporter":"Prabhjot Singh","Priority":"P4-Low","Status":"Completed","Assignee":"Prabhjot Singh","SLA Status":"Met","Created":"2026-03-07T12:00:00.000+0000","Resolved":"2026-03-07T14:09:00.000+0000" },
  { "Issue key":"GNOC-11591","Time to Resolution (Minutes)":1094,"Summary":"Alert: Lost service via VPLMN Vodafone Libertel B.V. - Ziggo (NSI)","Investigation Type":"MNO/VPLMN Issue","Source / Detection":"Alert","Reporter":"Yash Vijay Jadhav","Priority":"P4-Low","Status":"Completed","Assignee":"Yash Vijay Jadhav","SLA Status":"Met","Created":"2026-03-08T08:00:00.000+0000","Resolved":"2026-03-09T02:14:00.000+0000" },
  { "Issue key":"GNOC-11593","Time to Resolution (Minutes)":450,"Summary":"Alert: Lost service via VPLMN Orange Guinée (NSI)","Investigation Type":"MNO/VPLMN Issue","Source / Detection":"Alert","Reporter":"Ashay Matekar","Priority":"P4-Low","Status":"Completed","Assignee":"Ashay Matekar","SLA Status":"Met","Created":"2026-03-09T02:00:00.000+0000","Resolved":"2026-03-09T09:30:00.000+0000" },
  { "Issue key":"GNOC-11629","Time to Resolution (Minutes)":24,"Summary":"Alert: System Failure elevation for MNO Telekom Deutschland GmbH (T-Mobile)(NSI)","Investigation Type":"MNO/VPLMN Issue","Source / Detection":"Alert","Reporter":"Neha Kore","Priority":"P4-Low","Status":"Completed","Assignee":"Neha Kore","SLA Status":"Met","Created":"2026-03-10T09:00:00.000+0000","Resolved":"2026-03-10T09:24:00.000+0000" },
  { "Issue key":"GNOC-11631","Time to Resolution (Minutes)":74,"Summary":"Alert: Lost service via VPLMN Orange Cameroun SA","Investigation Type":"MNO/VPLMN Issue","Source / Detection":"Alert","Reporter":"Neha Kore","Priority":"P4-Low","Status":"Completed","Assignee":"Neha Kore","SLA Status":"Met","Created":"2026-03-10T09:30:00.000+0000","Resolved":"2026-03-10T10:44:00.000+0000" },
  { "Issue key":"GNOC-11584","Time to Resolution (Minutes)":359,"Summary":"HC/Alert: MT Voice Service Degradation – STIR/SHAKEN License Verification Failure (CSI)","Investigation Type":"Alert - NW Voice (STP/DEA/SMSC/VoLTE)","Source / Detection":"Health Check","Reporter":"Neha Kore","Priority":"P3-Medium","Status":"Completed","Assignee":"Neha Kore","SLA Status":"Met","Created":"2026-03-08T07:00:00.000+0000","Resolved":"2026-03-08T12:59:00.000+0000" },
  { "Issue key":"GNOC-11619","Time to Resolution (Minutes)":891,"Summary":"Alert: Multiple interface Down on rou-fkt-02.mobiquithings.com in Frankfurt production environment (NSI)","Investigation Type":"Alert - NW Data IP","Source / Detection":"Alert","Reporter":"Rajan Yadav","Priority":"P4-Low","Status":"Completed","Assignee":"Rajan Yadav","SLA Status":"Met","Created":"2026-03-10T04:00:00.000+0000","Resolved":"2026-03-10T18:51:00.000+0000" },
  { "Issue key":"GNOC-11559","Time to Resolution (Minutes)":4006,"Summary":"Alert : lspp-bos-wws72: Free space on volume: lspp-bos-wws72-C:\\ Label:Windows 9897E121","Investigation Type":"Alert - Infrastructure","Source / Detection":"Alert","Reporter":"Pranav Doshi","Priority":"P4-Low","Status":"Completed","Assignee":"Pranav Doshi","SLA Status":"Met","Created":"2026-03-07T06:00:00.000+0000","Resolved":"2026-03-09T00:46:00.000+0000" },
  { "Issue key":"GNOC-11605","Time to Resolution (Minutes)":2281,"Summary":"Alert : telco-account.aws: threshold of High Traffic on ELB_HTTP_Code_4XX exceeded: current value 140.000000 (NSI)","Investigation Type":"Alert - Infrastructure","Source / Detection":"Alert","Reporter":"Prabhjot Singh","Priority":"P4-Low","Status":"Completed","Assignee":"Prabhjot Singh","SLA Status":"Met","Created":"2026-03-09T10:00:00.000+0000","Resolved":"2026-03-11T00:01:00.000+0000" },
];

// ─── Past Weekly Data (W3-W6) ───
const PAST_WEEKS_INITIAL = [
  { week:"W3", created:12, resolved:10, p1:0, p2:0, p3:0, p4:12, mttr:39, p1Mttr:0, p2Mttr:0, p3Mttr:0, p4Mttr:39, backlogHours:"NA", backlogVol:"NA", majorP1P2:0, backlogAgingHours:"NA", backlogTicketVol:"NA" },
  { week:"W4", created:16, resolved:16, p1:0, p2:0, p3:0, p4:16, mttr:6, p1Mttr:0, p2Mttr:0, p3Mttr:0, p4Mttr:6, backlogHours:"NA", backlogVol:"NA", majorP1P2:0, backlogAgingHours:"NA", backlogTicketVol:"NA" },
  { week:"W5", created:10, resolved:10, p1:0, p2:0, p3:0, p4:10, mttr:29, p1Mttr:0, p2Mttr:0, p3Mttr:0, p4Mttr:29, backlogHours:"NA", backlogVol:"NA", majorP1P2:0, backlogAgingHours:"NA", backlogTicketVol:"NA" },
  { week:"W6", created:18, resolved:18, p1:0, p2:0, p3:0, p4:13, mttr:13, p1Mttr:0, p2Mttr:0, p3Mttr:0, p4Mttr:25, backlogHours:"NA", backlogVol:"NA", majorP1P2:0, backlogAgingHours:"NA", backlogTicketVol:"NA" },
];

// ─── CSV Parser ───
function parseCSV(text) {
  const lines = text.split("\n").filter(l => l.trim());
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
  return lines.slice(1).map(line => {
    const vals = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      if (line[i] === '"') { inQuotes = !inQuotes; }
      else if (line[i] === ',' && !inQuotes) { vals.push(current.trim()); current = ""; }
      else { current += line[i]; }
    }
    vals.push(current.trim());
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] || ""; });
    return obj;
  });
}

// ─── Pie Chart Component ───
function PieChart({ data, title, width = 320, height = 280 }) {
  const ref = useRef();

  useEffect(() => {
    if (!ref.current || !data || data.length === 0) return;
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();

    const radius = Math.min(width, height) / 2 - 40;
    const g = svg.append("g").attr("transform", `translate(${width/2},${height/2 + 10})`);

    const pie = d3.pie().value(d => d.value).sort(null);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);
    const labelArc = d3.arc().innerRadius(radius * 0.65).outerRadius(radius * 0.65);

    const total = d3.sum(data, d => d.value);
    const arcs = g.selectAll(".arc").data(pie(data)).enter().append("g");

    arcs.append("path")
      .attr("d", arc)
      .attr("fill", (d, i) => PIE_COLORS[i % PIE_COLORS.length])
      .attr("stroke", C.bg)
      .attr("stroke-width", 2)
      .style("opacity", 0)
      .transition().duration(600).delay((d, i) => i * 80).style("opacity", 1);

    arcs.append("text")
      .attr("transform", d => `translate(${labelArc.centroid(d)})`)
      .attr("text-anchor", "middle")
      .attr("fill", "#fff")
      .style("font-size", "11px")
      .style("font-weight", "600")
      .text(d => d.data.value > 0 ? (title.includes("Detection") ? `${((d.data.value/total)*100).toFixed(1)}%` : d.data.value) : "");

    svg.append("text")
      .attr("x", width/2).attr("y", 20)
      .attr("text-anchor", "middle")
      .attr("fill", C.white)
      .style("font-size", "15px")
      .style("font-weight", "700")
      .style("font-family", "'DM Sans', sans-serif")
      .text(title);

  }, [data, title, width, height]);

  return (
    <div style={{ background: C.card, borderRadius: 12, border: `1px solid ${C.border}`, padding: "12px 8px" }}>
      <svg ref={ref} width={width} height={height} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "4px 12px 8px", justifyContent: "center" }}>
        {data.map((d, i) => (
          <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.muted }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length] }} />
            <span>{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main App ───
export default function App() {
  const [data, setData] = useState(SAMPLE_DATA);
  const [sortCol, setSortCol] = useState("Issue key");
  const [sortDir, setSortDir] = useState("asc");
  const [filters, setFilters] = useState({ priority: "All", status: "All", investigation: "All", detection: "All", reporter: "All" });
  const [searchTerm, setSearchTerm] = useState("");
  const fileRef = useRef();

  // CSV upload handler
  const handleUpload = useCallback((e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const parsed = parseCSV(ev.target.result);
      if (parsed.length > 0) setData(parsed);
    };
    reader.readAsText(file);
  }, []);

  // Filtered data
  const filtered = useMemo(() => {
    return data.filter(row => {
      if (filters.priority !== "All" && row["Priority"] !== filters.priority) return false;
      if (filters.status !== "All" && row["Status"] !== filters.status) return false;
      if (filters.investigation !== "All" && row["Investigation Type"] !== filters.investigation) return false;
      if (filters.detection !== "All" && row["Source / Detection"] !== filters.detection) return false;
      if (filters.reporter !== "All" && row["Reporter"] !== filters.reporter) return false;
      if (searchTerm && !Object.values(row).some(v => String(v).toLowerCase().includes(searchTerm.toLowerCase()))) return false;
      return true;
    });
  }, [data, filters, searchTerm]);

  // Sorted data
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol];
      const na = parseFloat(va), nb = parseFloat(vb);
      if (!isNaN(na) && !isNaN(nb)) return sortDir === "asc" ? na - nb : nb - na;
      return sortDir === "asc" ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
  }, [filtered, sortCol, sortDir]);

  // Unique values for filters
  const uniqueVals = useCallback((key) => {
    const vals = [...new Set(data.map(r => r[key]).filter(Boolean))];
    return ["All", ...vals.sort()];
  }, [data]);

  // Cards
  const ticketsCreated = data.length;
  const ticketsResolved = data.filter(r => r["Status"]?.toLowerCase() === "completed" || r["Status"]?.toLowerCase() === "closed" || r["Resolved"]).length;
  const mttrMinutes = data.reduce((sum, r) => sum + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
  const mttrHours = ticketsResolved > 0 ? Math.round(mttrMinutes / ticketsResolved / 60) : 0;
  const slaBreach = data.filter(r => r["SLA Status"] === "Breached").length;

  // Pie data
  const investigationPie = useMemo(() => {
    const counts = _.countBy(filtered, "Investigation Type");
    return Object.entries(counts).filter(([k]) => k).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
  }, [filtered]);

  const detectionPie = useMemo(() => {
    const counts = _.countBy(filtered, "Source / Detection");
    return Object.entries(counts).filter(([k]) => k).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
  }, [filtered]);

  // Compute current week (W7) from loaded data
  const currentWeek = useMemo(() => {
    const created = data.length;
    const resolved = data.filter(r => r["Status"]?.toLowerCase() === "completed" || r["Status"]?.toLowerCase() === "closed" || r["Resolved"]).length;
    const p1 = data.filter(r => r["Priority"]?.includes("P1")).length;
    const p2 = data.filter(r => r["Priority"]?.includes("P2")).length;
    const p3 = data.filter(r => r["Priority"]?.includes("P3")).length;
    const p4 = data.filter(r => r["Priority"]?.includes("P4")).length;
    const totalMin = data.reduce((s, r) => s + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
    const mttr = resolved > 0 ? Math.round(totalMin / resolved / 60) : 0;
    const p1Min = data.filter(r => r["Priority"]?.includes("P1")).reduce((s, r) => s + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
    const p2Min = data.filter(r => r["Priority"]?.includes("P2")).reduce((s, r) => s + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
    const p3Min = data.filter(r => r["Priority"]?.includes("P3")).reduce((s, r) => s + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
    const p4Min = data.filter(r => r["Priority"]?.includes("P4")).reduce((s, r) => s + (parseFloat(r["Time to Resolution (Minutes)"]) || 0), 0);
    const p1Count = data.filter(r => r["Priority"]?.includes("P1")).length;
    const p2Count = data.filter(r => r["Priority"]?.includes("P2")).length;
    const p3Count = data.filter(r => r["Priority"]?.includes("P3")).length;
    const p4Count = data.filter(r => r["Priority"]?.includes("P4")).length;
    return {
      week: "W7", created, resolved,
      p1, p2, p3, p4, mttr,
      p1Mttr: p1Count > 0 ? Math.round(p1Min / p1Count / 60) : 0,
      p2Mttr: p2Count > 0 ? Math.round(p2Min / p2Count / 60) : 0,
      p3Mttr: p3Count > 0 ? Math.round(p3Min / p3Count / 60) : 0,
      p4Mttr: p4Count > 0 ? Math.round(p4Min / p4Count / 60) : 0,
      backlogHours: "NA", backlogVol: "NA",
      majorP1P2: p1 + p2,
      backlogAgingHours: "NA", backlogTicketVol: "NA"
    };
  }, [data]);

  const allWeeks = [...PAST_WEEKS_INITIAL, currentWeek];

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const tableCols = ["Issue key", "Time to Resolution (Minutes)", "Summary", "Investigation Type", "Source / Detection", "Reporter", "Priority", "Status", "SLA Status"];

  const selectStyle = {
    background: C.cardAlt, color: C.white, border: `1px solid ${C.border}`,
    borderRadius: 6, padding: "6px 10px", fontSize: 12, outline: "none", minWidth: 120, cursor: "pointer"
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.white, fontFamily: "'DM Sans', sans-serif", padding: "24px 28px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: "-0.5px" }}>
            <span style={{ color: C.accent }}>GNOC</span> Incident Dashboard
          </h1>
          <p style={{ margin: "4px 0 0", color: C.muted, fontSize: 13 }}>Weekly Incident Tracking & SLA Monitoring</p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`, color: "#fff",
              border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 13, fontWeight: 600,
              cursor: "pointer", display: "flex", alignItems: "center", gap: 6
            }}
          >
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M12 16V4m0 0L8 8m4-4l4 4M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Upload CSV
          </button>
          <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} style={{ display: "none" }} />
        </div>
      </div>

      {/* Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Tickets Created", value: ticketsCreated, icon: "📋", color: C.accent },
          { label: "Tickets Resolved", value: ticketsResolved, icon: "✅", color: C.green },
          { label: "MTTR (Hours)", value: mttrHours, icon: "⏱️", color: C.amber },
          { label: "SLA Breached", value: slaBreach, icon: "🚨", color: slaBreach > 0 ? C.red : C.green },
        ].map(card => (
          <div key={card.label} style={{
            background: C.card, borderRadius: 12, border: `1px solid ${C.border}`,
            padding: "20px 22px", display: "flex", alignItems: "center", gap: 16,
            boxShadow: "0 2px 12px rgba(0,0,0,0.2)"
          }}>
            <div style={{ fontSize: 30 }}>{card.icon}</div>
            <div>
              <div style={{ color: C.muted, fontSize: 12, fontWeight: 500, textTransform: "uppercase", letterSpacing: 0.5 }}>{card.label}</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: card.color, marginTop: 2 }}>{card.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{
        background: C.card, borderRadius: 12, border: `1px solid ${C.border}`,
        padding: "14px 18px", marginBottom: 20, display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flex: "1 1 200px" }}>
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke={C.muted} strokeWidth="2"/><path d="M21 21l-4-4" stroke={C.muted} strokeWidth="2" strokeLinecap="round"/></svg>
          <input
            placeholder="Search tickets..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{ ...selectStyle, flex: 1, minWidth: 180 }}
          />
        </div>
        {[
          { key: "priority", label: "Priority", field: "Priority" },
          { key: "status", label: "Status", field: "Status" },
          { key: "investigation", label: "Investigation", field: "Investigation Type" },
          { key: "detection", label: "Detection", field: "Source / Detection" },
          { key: "reporter", label: "Reporter", field: "Reporter" },
        ].map(f => (
          <select key={f.key} value={filters[f.key]} onChange={e => setFilters(prev => ({ ...prev, [f.key]: e.target.value }))} style={selectStyle}>
            {uniqueVals(f.field).map(v => <option key={v} value={v}>{v === "All" ? `${f.label}: All` : v}</option>)}
          </select>
        ))}
      </div>

      {/* Table + Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, marginBottom: 28 }}>
        {/* Incident Table */}
        <div style={{ background: C.card, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden" }}>
          <div style={{ overflowX: "auto", maxHeight: 480 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  {tableCols.map(col => (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      style={{
                        position: "sticky", top: 0, zIndex: 2,
                        background: C.headerBg, color: "#fff", padding: "10px 12px",
                        textAlign: "left", cursor: "pointer", whiteSpace: "nowrap",
                        fontWeight: 600, fontSize: 11, letterSpacing: 0.3,
                        borderBottom: `2px solid ${C.accent}`
                      }}
                    >
                      {col === "Time to Resolution (Minutes)" ? "TTR (Hrs)" : col}
                      {sortCol === col ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, i) => (
                  <tr key={row["Issue key"] || i} style={{ background: i % 2 === 0 ? C.tableBg : C.card, transition: "background 0.15s" }}
                    onMouseEnter={e => e.currentTarget.style.background = C.rowHover}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? C.tableBg : C.card}
                  >
                    {tableCols.map(col => {
                      let val = row[col];
                      if (col === "Time to Resolution (Minutes)") val = (parseFloat(val) / 60).toFixed(2);
                      const isPriority = col === "Priority";
                      const isSLA = col === "SLA Status";
                      let badge = null;
                      if (isPriority && val) {
                        const c = val.includes("P1") ? C.red : val.includes("P2") ? C.amber : val.includes("P3") ? C.purple : C.cyan;
                        badge = <span style={{ background: c + "22", color: c, padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>{val}</span>;
                      }
                      if (isSLA) {
                        const c = val === "Breached" ? C.red : C.green;
                        badge = <span style={{ background: c + "22", color: c, padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>{val || "—"}</span>;
                      }
                      return (
                        <td key={col} style={{
                          padding: "8px 12px", borderBottom: `1px solid ${C.border}`,
                          whiteSpace: col === "Summary" ? "normal" : "nowrap",
                          maxWidth: col === "Summary" ? 280 : "auto",
                          color: C.muted, fontSize: 11.5
                        }}>
                          {badge || val || "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "8px 16px", color: C.dimmed, fontSize: 11, borderTop: `1px solid ${C.border}` }}>
            Showing {sorted.length} of {data.length} tickets
          </div>
        </div>

        {/* Pie Charts */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <PieChart data={investigationPie} title="Investigation Type" width={320} height={240} />
          <PieChart data={detectionPie} title="Detection Type" width={320} height={240} />
        </div>
      </div>

      {/* Weekly Summary Tables */}
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 14, color: C.white }}>
          Weekly Summary <span style={{ color: C.accent, fontSize: 13, fontWeight: 500 }}>— Trend Data</span>
        </h2>

        {/* Top Table */}
        <div style={{ background: C.card, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden", marginBottom: 18 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "center" }}>
            <thead>
              <tr>
                <th style={{ background: C.headerBg, color: "#fff", padding: "10px 14px", textAlign: "left", fontWeight: 700, width: 180 }}></th>
                {allWeeks.map(w => (
                  <th key={w.week} style={{ background: C.headerBg, color: "#fff", padding: "10px 14px", fontWeight: 700, minWidth: 70 }}>{w.week}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { label: "Tickets Created", key: "created", bg: C.headerBg },
                { label: "Tickets Resolved", key: "resolved", bg: C.headerBg },
                { label: "P1 Tickets", key: "p1", bg: C.headerBg },
                { label: "P2 Tickets", key: "p2", bg: C.headerBg },
                { label: "P3 Tickets", key: "p3", bg: C.headerBg },
                { label: "P4 Tickets", key: "p4", bg: C.headerBg },
                { label: "MTTR (hours)", key: "mttr", bg: C.weekOrange },
                { label: "P1 - MTTR", key: "p1Mttr", bg: C.weekOrange },
                { label: "P2 - MTTR", key: "p2Mttr", bg: C.weekOrange },
                { label: "P3 - MTTR", key: "p3Mttr", bg: C.weekOrange },
                { label: "P4 - MTTR", key: "p4Mttr", bg: C.weekOrange },
                { label: "Backlog Aging (HOURS)", key: "backlogHours", bg: C.weekBlack },
                { label: "Backlog Ticket Volume", key: "backlogVol", bg: C.weekBlack },
              ].map((row, ri) => (
                <tr key={row.key}>
                  <td style={{
                    background: row.bg, color: "#fff", padding: "8px 14px",
                    textAlign: "left", fontWeight: 600, fontSize: 12, borderBottom: `1px solid ${C.border}`
                  }}>{row.label}</td>
                  {allWeeks.map((w, wi) => (
                    <td key={w.week} style={{
                      padding: "8px 14px", fontWeight: 600,
                      background: wi === allWeeks.length - 1 ? C.accent + "18" : (ri % 2 === 0 ? C.tableBg : C.card),
                      color: wi === allWeeks.length - 1 ? C.accentLight : C.muted,
                      borderBottom: `1px solid ${C.border}`
                    }}>{w[row.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bottom Summary Table */}
        <div style={{ background: C.card, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "center" }}>
            <thead>
              <tr>
                <th style={{ background: C.weekCyan, color: "#fff", padding: "10px 14px", textAlign: "left", fontWeight: 700, width: 180 }}></th>
                {allWeeks.map(w => (
                  <th key={w.week} style={{ background: C.weekCyan, color: "#fff", padding: "10px 14px", fontWeight: 700, minWidth: 70 }}>{w.week}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { label: "Tickets Created", key: "created" },
                { label: "Major (P1/P2) Incidents", key: "majorP1P2" },
                { label: "Overall MTTR (hours)", key: "mttr" },
                { label: "Backlog Aging (HOURS)", key: "backlogAgingHours" },
                { label: "Backlog Ticket Volume", key: "backlogTicketVol" },
              ].map((row, ri) => (
                <tr key={row.key + "_bottom"}>
                  <td style={{
                    background: C.weekCyan, color: "#fff", padding: "8px 14px",
                    textAlign: "left", fontWeight: 600, fontSize: 12, borderBottom: `1px solid ${C.border}`
                  }}>{row.label}</td>
                  {allWeeks.map((w, wi) => (
                    <td key={w.week} style={{
                      padding: "8px 14px", fontWeight: 600,
                      background: wi === allWeeks.length - 1 ? C.cyan + "15" : (ri % 2 === 0 ? C.tableBg : C.card),
                      color: wi === allWeeks.length - 1 ? C.cyan : C.muted,
                      borderBottom: `1px solid ${C.border}`
                    }}>{w[row.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

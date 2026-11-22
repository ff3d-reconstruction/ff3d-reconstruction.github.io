// Browser-native helpers for the survey website.
// Exports: filterMethods, filterDatasets, sortRows, csvText

const norm = (v) => (v == null ? "" : String(v));

function text(record, ...keys) {
  return keys.map((key) => (record ? record[key] : "")).map(norm);
}

function contains(haystacks, needle) {
  if (!needle) return true;
  const q = needle.toLowerCase();
  return haystacks.some((h) => h.toLowerCase().includes(q));
}

function asArray(value) {
  return Array.isArray(value) ? value : value == null ? [] : [value];
}

export function filterMethods(rows, { query = "", mechanism = "" } = {}) {
  const list = Array.isArray(rows) ? rows : [];
  const q = query == null ? "" : String(query).trim();
  const mech = mechanism == null ? "" : String(mechanism).trim();
  return list.filter((row) => {
    if (!row) return false;
    if (mech && norm(row.mechanism) !== mech) return false;
    const fields = text(row, "name", "title", "venue", "mechanism", "settings");
    fields.push(norm(row.year));
    return contains(fields, q);
  });
}

export function filterDatasets(rows, { query = "", scene = "", projection = "" } = {}) {
  const list = Array.isArray(rows) ? rows : [];
  const q = query == null ? "" : String(query).trim();
  const sc = scene == null ? "" : String(scene).trim();
  const proj = projection == null ? "" : String(projection).trim();
  return list.filter((row) => {
    if (!row) return false;
    if (sc && norm(row.domain).trim() !== sc) return false;
    if (proj && !asArray(row.projection).some((p) => norm(p).trim() === proj)) return false;
    const fields = [
      ...text(row, "name", "domain", "origin", "observations", "reference"),
      ...asArray(row.projection).map(norm),
    ];
    return contains(fields, q);
  });
}

function numericValue(v) {
  if (v == null) return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function compareValues(a, b) {
  const na = numericValue(a);
  const nb = numericValue(b);
  if (na != null && nb != null) return na < nb ? -1 : na > nb ? 1 : 0;
  if (na != null) return -1;
  if (nb != null) return 1;
  const sa = norm(a).toLowerCase();
  const sb = norm(b).toLowerCase();
  return sa < sb ? -1 : sa > sb ? 1 : 0;
}

function keyOf(row, key) {
  if (row == null) return null;
  if (typeof key === "function") return key(row);
  return row[key];
}

export function sortRows(rows, key, direction = "asc") {
  const list = Array.isArray(rows) ? rows : [];
  const sign = String(direction).toLowerCase() === "desc" ? -1 : 1;
  const keyed = list.map((row, index) => ({ row, index, value: keyOf(row, key) }));
  const empty = (v) => v == null || (typeof v === "string" && v.trim() === "");
  keyed.sort((a, b) => {
    const ea = empty(a.value);
    const eb = empty(b.value);
    if (ea && eb) return a.index - b.index;
    if (ea) return 1;
    if (eb) return -1;
    const c = compareValues(a.value, b.value);
    if (c !== 0) return c * sign;
    return a.index - b.index;
  });
  return keyed.map((entry) => entry.row);
}

function csvField(value) {
  if (value == null) return "";
  const s = String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function csvText(rows, columns) {
  const cols = asArray(columns);
  const list = Array.isArray(rows) ? rows : [];
  const esc = (line) => {
    const formatted = cols.map((col) => csvField(line == null ? null : line[col.key]));
    return formatted.join(",");
  };
  const lines = [cols.map((col) => csvField(col.label)).join(","), ...list.map(esc)];
  return lines.join("\r\n");
}

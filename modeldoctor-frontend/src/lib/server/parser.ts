/* ────────────────────────────────────────
   Layer 1: Code Parser — structural intelligence.
   TypeScript port of services/parser.py.
   Line/regex based analysis of Python source.
   ──────────────────────────────────────── */

export interface CallInfo {
  line: number;
  method?: string;
  function?: string;
  object?: string;
}

export interface ImportInfo {
  module: string;
  alias: string | null;
  line: number;
}

export interface ParsedCode {
  code: string;
  parseSuccess: boolean;
  error: string | null;
  imports: { importList: ImportInfo[]; frameworks: string[] };
  assignments: Record<string, number[]>;
  usages: Record<string, number[]>;
  callsInOrder: CallInfo[];
  functionDefs: { name: string; line: number; args: string[] }[];
  classes: { name: string; line: number }[];
}

const ML_LIBS = new Set([
  "sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "scipy",
]);
const DL_LIBS = new Set([
  "tensorflow", "keras", "torch", "pytorch", "transformers", "jax",
]);
const DATA_LIBS = new Set(["pandas", "numpy", "polars", "dask"]);

/**
 * Remove a trailing `#` comment, respecting quoted strings.
 */
function stripComment(line: string): string {
  let inS = false;
  let inD = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === "\\") {
      i++;
      continue;
    }
    if (c === "'" && !inD) inS = !inS;
    else if (c === '"' && !inS) inD = !inD;
    else if (c === "#" && !inS && !inD) return line.slice(0, i);
  }
  return line;
}

function push(map: Record<string, number[]>, key: string, line: number) {
  (map[key] ||= []).push(line);
}

function analyzeImports(lines: string[]): ParsedCode["imports"] {
  const importList: ImportInfo[] = [];
  const frameworks = new Set<string>();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNo = i + 1;

    let m = /^\s*import\s+([A-Za-z_][\w.]*)\s*(?:as\s+([A-Za-z_]\w*))?/.exec(line);
    if (m) {
      const module = m[1];
      importList.push({ module, alias: m[2] ?? null, line: lineNo });
      const root = module.split(".")[0];
      if (ML_LIBS.has(root) || DL_LIBS.has(root) || DATA_LIBS.has(root)) {
        frameworks.add(root);
      }
      continue;
    }

    m = /^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+(.+)$/.exec(line);
    if (m) {
      const module = m[1];
      const root = module.split(".")[0];
      for (const part of m[2].split(",")) {
        const namePart = part.trim().split(/\s+as\s+/);
        if (!namePart[0]) continue;
        const symbol = namePart[0] === "*" ? "*" : namePart[0].split(".")[0];
        importList.push({
          module: `${module}.${symbol}`,
          alias: namePart[1] ?? null,
          line: lineNo,
        });
      }
      if (ML_LIBS.has(root) || DL_LIBS.has(root) || DATA_LIBS.has(root)) {
        frameworks.add(root);
      }
    }
  }

  return { importList, frameworks: Array.from(frameworks).sort() };
}

function analyzeVariableFlow(lines: string[]): {
  assignments: Record<string, number[]>;
  usages: Record<string, number[]>;
} {
  const assignments: Record<string, number[]> = {};
  const usages: Record<string, number[]> = {};

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNo = i + 1;

    // Assignments: `a = ...`, `a, b = ...`, `a += ...`
    const m = /^\s*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*(?:=|\+=|-=|\*=|\/=)(?!=)/.exec(line);
    const assigned: string[] = [];
    if (m) {
      for (const name of m[1].split(",")) {
        const id = name.trim();
        if (id) {
          push(assignments, id, lineNo);
          assigned.push(id);
        }
      }
    }

    // Names referenced on this line (approximate "load" context).
    const nameRe = /[A-Za-z_]\w*/g;
    let nameMatch: RegExpExecArray | null;
    while ((nameMatch = nameRe.exec(line)) !== null) {
      if (!assigned.includes(nameMatch[0])) {
        push(usages, nameMatch[0], lineNo);
      }
    }
  }

  return { assignments, usages };
}

function extractCallInfo(body: string, lineNo: number): CallInfo | null {
  // `a.b.c(` — attribute call — or `name(` — plain function call.
  const attr = /([A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)+)\s*\(/.exec(body);
  if (attr) {
    const parts = attr[1].split(".").map((p) => p.trim());
    const info: CallInfo = { line: lineNo, method: parts[parts.length - 1] };
    if (parts.length === 2) info.object = parts[0];
    return info;
  }
  const fn = /(?:^|[^\w.])([A-Za-z_]\w*)\s*\(/.exec(body);
  if (fn) return { line: lineNo, function: fn[1] };
  return null;
}

function analyzeStructure(lines: string[]): Pick<
  ParsedCode,
  "callsInOrder" | "functionDefs" | "classes"
> {
  const callsInOrder: CallInfo[] = [];
  const functionDefs: ParsedCode["functionDefs"] = [];
  const classes: ParsedCode["classes"] = [];

  lines.forEach((body, i) => {
    const lineNo = i + 1;
    const indent = /^\s*/.exec(body)![0].length;
    const trimmed = body.trim();

    if (indent === 0) {
      const fn = /^(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)/.exec(trimmed);
      if (fn) {
        const args = fn[2]
          .split(",")
          .map((a) => a.split("=")[0].trim().replace(/^[*]+/, ""))
          .filter(Boolean);
        functionDefs.push({ name: fn[1], line: lineNo, args });
      }
      const cls = /^class\s+([A-Za-z_]\w*)/.exec(trimmed);
      if (cls) classes.push({ name: cls[1], line: lineNo });
    }

    if (!trimmed) return;

    // Keyword-definition lines are not call sites themselves.
    if (/^(?:async\s+)?(?:def|class|if|elif|else|for|while|return|import|from)\b/.test(trimmed)) {
      return;
    }

    const call = extractCallInfo(trimmed, lineNo);
    if (call) callsInOrder.push(call);
  });

  callsInOrder.sort((a, b) => a.line - b.line);
  return { callsInOrder, functionDefs, classes };
}

/**
 * Basic structural sanity check: balanced brackets, and a leading
 * `def`/`class` (a sign the user pasted a fragment).
 * Mirrors the intent of `ast.parse` failing, without a Python runtime.
 */
function parseErrors(lines: string[]): string[] {
  const errors: string[] = [];
  let depth = 0;

  for (let i = 0; i < lines.length; i++) {
    for (const ch of stripComment(lines[i])) {
      if (ch === "(" || ch === "[" || ch === "{") depth++;
      else if (ch === ")" || ch === "]" || ch === "}") depth--;
      if (depth < 0) {
        errors.push(`Unmatched closing bracket on line ${i + 1}`);
        depth = 0;
      }
    }
  }
  if (depth > 0) errors.push(`${depth} unclosed bracket(s) in the snippet`);

  const first = (lines[0] ?? "").trim();
  if (/^(?:def|class)\b/.test(first) && (lines[1] ?? "").trim() === "") {
    errors.push("Snippet starts with a def/class declaration (possible fragment)");
  }
  return errors;
}

export function parseCode(code: string): ParsedCode {
  const rawLines = code.split("\n");
  const errors = parseErrors(rawLines);

  if (errors.length) {
    return {
      code,
      parseSuccess: false,
      error: errors[0],
      imports: { importList: [], frameworks: [] },
      assignments: {},
      usages: {},
      callsInOrder: [],
      functionDefs: [],
      classes: [],
    };
  }

  const lines = rawLines.map(stripComment);
  const { assignments, usages } = analyzeVariableFlow(lines);
  const structure = analyzeStructure(lines);

  return {
    code,
    parseSuccess: true,
    error: null,
    imports: analyzeImports(lines),
    assignments,
    usages,
    ...structure,
  };
}

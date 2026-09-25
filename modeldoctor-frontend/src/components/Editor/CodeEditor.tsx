/* ────────────────────────────────────────
   CodeEditor — Monaco editor wrapper
   with file tab bar, syntax highlighting,
   and live scan markers
   ──────────────────────────────────────── */

"use client";

import { useRef, useEffect } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { QuickScanFlag } from "@/lib/types";

const SEVERITY_MARKER_CLASS: Record<string, string> = {
  CRITICAL: "live-marker-critical",
  HIGH: "live-marker-high",
  MEDIUM: "live-marker-medium",
  LOW: "live-marker-low",
};

const SEVERITY_MONACO: Record<string, number> = {
  CRITICAL: 8, // MarkerSeverity.Error
  HIGH: 8,
  MEDIUM: 4,   // MarkerSeverity.Warning
  LOW: 2,      // MarkerSeverity.Info
};

interface CodeEditorProps {
  code: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  liveFlags?: QuickScanFlag[];
}

export default function CodeEditor({
  code,
  onChange,
  disabled = false,
  liveFlags = [],
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);
  const decorationsRef = useRef<string[]>([]);

  const handleEditorMount: OnMount = (editorInstance, monaco) => {
    editorRef.current = editorInstance;
    monacoRef.current = monaco;
    editorInstance.focus();
  };

  // Update Monaco markers when liveFlags change
  useEffect(() => {
    const editorInstance = editorRef.current;
    const monaco = monacoRef.current;
    if (!editorInstance || !monaco) return;

    const model = editorInstance.getModel();
    if (!model) return;

    // Set Monaco markers (squiggly underlines)
    const markers = liveFlags
      .filter((f) => f.line_number)
      .map((f) => ({
        severity: (SEVERITY_MONACO[f.severity] || 4) as import("monaco-editor").MarkerSeverity,
        startLineNumber: f.line_number!,
        endLineNumber: f.line_number!,
        startColumn: 1,
        endColumn: model.getLineMaxColumn(f.line_number!),
        message: `[${f.severity}] ${f.pattern_name}\n${f.description}`,
        source: "ModelDoctor",
      }));

    monaco.editor.setModelMarkers(model, "modeldoctor-live", markers);

    // Set line decorations (colored gutter + line background)
    const decorations: editor.IModelDeltaDecoration[] = liveFlags
      .filter((f) => f.line_number)
      .map((f) => ({
        range: {
          startLineNumber: f.line_number!,
          endLineNumber: f.line_number!,
          startColumn: 1,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: SEVERITY_MARKER_CLASS[f.severity] || "live-marker-low",
          glyphMarginClassName:
            f.severity === "CRITICAL" || f.severity === "HIGH"
              ? "glyph-marker-error"
              : "glyph-marker-warn",
          glyphMarginHoverMessage: {
            value: `**${f.pattern_name}** (${f.severity})\n\n${f.description}`,
          },
          hoverMessage: {
            value: `**🩺 ModelDoctor Live Scan**\n\n**${f.pattern_name}**\n\n${f.description}`,
          },
        },
      }));

    decorationsRef.current = editorInstance.deltaDecorations(
      decorationsRef.current,
      decorations
    );

    return () => {
      // Cleanup markers on unmount
      monaco.editor.setModelMarkers(model, "modeldoctor-live", []);
    };
  }, [liveFlags]);

  return (
    <div className="editor-container glass rounded-xl overflow-hidden">
      {/* Tab Bar */}
      <div className="flex items-center gap-2 px-4 py-2 bg-void/80 border-b border-white/[0.05]">
        {/* Traffic lights */}
        <div className="flex gap-1.5 mr-3">
          <div className="w-2.5 h-2.5 rounded-full bg-accent-red/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-accent-yellow/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-accent-teal/70" />
        </div>

        {/* File tab */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.05] text-[11px] text-text-primary font-mono">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2">
            <path d="M13.5 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8.5L13.5 3z" />
            <polyline points="13,3 13,9 19,9" />
          </svg>
          pipeline.py
        </div>

        <span className="text-[10px] text-text-muted/40 ml-auto font-mono">
          Python
        </span>
      </div>

      {/* Monaco Editor */}
      <Editor
        height="420px"
        defaultLanguage="python"
        value={code}
        onChange={(value) => onChange(value || "")}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          fontSize: 13,
          fontFamily: "var(--font-mono), 'JetBrains Mono', 'Fira Code', monospace",
          lineNumbers: "on",
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          padding: { top: 16, bottom: 16 },
          renderLineHighlight: "gutter",
          cursorBlinking: "smooth",
          smoothScrolling: true,
          readOnly: disabled,
          wordWrap: "on",
          automaticLayout: true,
          tabSize: 4,
          bracketPairColorization: { enabled: true },
          guides: { indentation: true },
          glyphMargin: liveFlags.length > 0,
        }}
      />
    </div>
  );
}

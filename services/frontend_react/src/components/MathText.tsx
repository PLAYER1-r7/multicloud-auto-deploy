import katex from "katex";
import "katex/dist/katex.min.css";

interface Props {
  /** $...$ (inline) / $$...$$ (display) を含むテキスト */
  text: string;
  className?: string;
}

/**
 * テキスト中の $...$ と $$...$$ を KaTeX でレンダリングするコンポーネント。
 * それ以外の部分はプレーンテキスト / 改行として表示する。
 */
export default function MathText({ text, className }: Props) {
  const nodes = parseSegments(text);

  return (
    <span className={className}>
      {nodes.map((seg, i) => {
        if (seg.type === "text") {
          // 改行を <br> に変換
          return seg.value.split("\n").map((line, j, arr) => (
            <span key={`${i}-${j}`}>
              {line}
              {j < arr.length - 1 && <br />}
            </span>
          ));
        }
        // math
        try {
          const html = katex.renderToString(seg.value, {
            displayMode: seg.display,
            throwOnError: false,
            output: "html",
          });
          return (
            <span
              key={i}
              dangerouslySetInnerHTML={{ __html: html }}
              style={
                seg.display
                  ? { display: "block", margin: "0.6em 0" }
                  : undefined
              }
            />
          );
        } catch {
          // フォールバック: 生テキスト
          return (
            <code key={i} style={{ fontSize: "0.9em" }}>
              {seg.display ? `$$${seg.value}$$` : `$${seg.value}$`}
            </code>
          );
        }
      })}
    </span>
  );
}

// ─────────────────────────────────────────────────────
type Segment =
  | { type: "text"; value: string }
  | { type: "math"; value: string; display: boolean };

/** $$...$$ → inline $...$ の順にパースする */
function parseSegments(src: string): Segment[] {
  const result: Segment[] = [];
  let rest = src;

  while (rest.length > 0) {
    // --- display math $$...$$
    const ddStart = rest.indexOf("$$");
    // --- inline math $...$
    const dStart = rest.search(/(?<!\$)\$(?!\$)/);

    if (ddStart === -1 && dStart === -1) {
      result.push({ type: "text", value: rest });
      break;
    }

    // どちらが先か
    const first =
      ddStart === -1
        ? "inline"
        : dStart === -1
          ? "display"
          : ddStart <= dStart
            ? "display"
            : "inline";

    if (first === "display") {
      if (ddStart > 0) {
        result.push({ type: "text", value: rest.slice(0, ddStart) });
      }
      const ddEnd = rest.indexOf("$$", ddStart + 2);
      if (ddEnd === -1) {
        result.push({ type: "text", value: rest });
        break;
      }
      result.push({
        type: "math",
        value: rest.slice(ddStart + 2, ddEnd),
        display: true,
      });
      rest = rest.slice(ddEnd + 2);
    } else {
      if (dStart > 0) {
        result.push({ type: "text", value: rest.slice(0, dStart) });
      }
      const dEnd = rest.search(new RegExp(`(?<!\\$)\\$(?!\\$)`, ""));
      const closeIdx = rest.indexOf("$", dStart + 1);
      if (closeIdx === -1) {
        result.push({ type: "text", value: rest });
        break;
      }
      result.push({
        type: "math",
        value: rest.slice(dStart + 1, closeIdx),
        display: false,
      });
      rest = rest.slice(closeIdx + 1);
      void dEnd; // suppress unused warning
    }
  }

  return result;
}

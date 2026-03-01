/**
 * MathGraph3D – Plotly.js を使った 3D 座標グラフコンポーネント
 *
 * PlotData.dimension === 3 の場合に SolverPage から呼ばれる。
 * react-plotly.js の動的インポートで初回バンドルサイズを抑制する。
 */
import React, { useMemo } from "react";
import Plot from "react-plotly.js";
import { evaluate } from "mathjs";
import type {
  PlotData,
  PlotPoint3D,
  PlotLine3D,
  PlotPlane3D,
  PlotSurface3D,
  PlotViewRange3D,
} from "../types/solve";

// Plotly トレース型（最低限）
type PlotlyData = Parameters<typeof Plot>[0]["data"][number];

// ─── グリッド生成ヘルパー ─────────────────────────────────────
function linspace(min: number, max: number, n = 30): number[] {
  const arr: number[] = [];
  for (let i = 0; i < n; i++) {
    arr.push(min + (i / (n - 1)) * (max - min));
  }
  return arr;
}

// ─── トレース変換 ────────────────────────────────────────────────

function pointsTrace(points: PlotPoint3D[]): PlotlyData {
  return {
    type: "scatter3d",
    mode: "markers+text",
    x: points.map((p) => p.x),
    y: points.map((p) => p.y),
    z: points.map((p) => p.z),
    text: points.map((p) => p.label ?? ""),
    textposition: "top center",
    marker: { size: 6, color: "#3b82f6" },
    name: "点",
  } as PlotlyData;
}

function linesTrace(lines: PlotLine3D[]): PlotlyData[] {
  return lines.map((seg, idx) => ({
    type: "scatter3d",
    mode: "lines+text",
    x: [seg.from[0], seg.to[0]],
    y: [seg.from[1], seg.to[1]],
    z: [seg.from[2], seg.to[2]],
    text: ["", seg.label ?? ""],
    textposition: "top right",
    line: { color: "#ef4444", width: 4 },
    name: seg.label ?? `線分${idx + 1}`,
  })) as PlotlyData[];
}

function planeTrace(plane: PlotPlane3D): PlotlyData | null {
  const { a, b, c, d, xRange, yRange, label } = plane;
  if (c === 0) return null; // z を表せない平面は省略

  const xs = linspace(xRange[0], xRange[1], 20);
  const ys = linspace(yRange[0], yRange[1], 20);
  const zGrid: number[][] = ys.map((y) =>
    xs.map((x) => (d - a * x - b * y) / c)
  );

  return {
    type: "surface",
    x: xs,
    y: ys,
    z: zGrid,
    opacity: 0.45,
    colorscale: [[0, "#a78bfa"], [1, "#c4b5fd"]],
    showscale: false,
    name: label ?? "平面",
  } as PlotlyData;
}

function surfaceTrace(surf: PlotSurface3D): PlotlyData | null {
  const { fnZ, xRange, yRange, label } = surf;
  try {
    const xs = linspace(xRange[0], xRange[1], 30);
    const ys = linspace(yRange[0], yRange[1], 30);
    const zGrid: number[][] = ys.map((y) =>
      xs.map((x) => {
        const val = evaluate(fnZ, { x, y });
        return typeof val === "number" && isFinite(val) ? val : null;
      })
    );

    return {
      type: "surface",
      x: xs,
      y: ys,
      z: zGrid,
      opacity: 0.7,
      colorscale: "Viridis",
      showscale: true,
      name: label ?? fnZ,
    } as PlotlyData;
  } catch {
    return null;
  }
}

// ─── Plotly レイアウト ────────────────────────────────────────────

function buildLayout(viewRange?: PlotViewRange3D) {
  const axisBase = {
    showgrid: true,
    gridcolor: "#e5e7eb",
    showline: true,
    zerolinecolor: "#6b7280",
    zerolinewidth: 2,
    tickfont: { size: 10 },
  };

  const scene: Record<string, unknown> = {
    xaxis: { ...axisBase, title: { text: "x" }, ...(viewRange ? { range: viewRange.xRange } : {}) },
    yaxis: { ...axisBase, title: { text: "y" }, ...(viewRange ? { range: viewRange.yRange } : {}) },
    zaxis: { ...axisBase, title: { text: "z" }, ...(viewRange ? { range: viewRange.zRange } : {}) },
    aspectmode: "auto",
    bgcolor: "#f9fafb",
  };

  return {
    scene,
    margin: { l: 0, r: 0, t: 30, b: 0 },
    paper_bgcolor: "#f9fafb",
    legend: { orientation: "h" as const, x: 0, y: -0.05 },
    font: { family: "system-ui, sans-serif", size: 12 },
    height: 480,
  };
}

// ─── メインコンポーネント ─────────────────────────────────────────

interface MathGraph3DProps {
  data: PlotData;
}

const MathGraph3D: React.FC<MathGraph3DProps> = ({ data }) => {
  const traces = useMemo<PlotlyData[]>(() => {
    const result: PlotlyData[] = [];

    // 点
    if (data.points3d && data.points3d.length > 0) {
      result.push(pointsTrace(data.points3d));
    }

    // 線分
    if (data.lines3d && data.lines3d.length > 0) {
      result.push(...linesTrace(data.lines3d));
    }

    // 平面 (ax+by+cz=d)
    if (data.planes3d) {
      for (const plane of data.planes3d) {
        const tr = planeTrace(plane);
        if (tr) result.push(tr);
      }
    }

    // 曲面 (z=f(x,y))
    if (data.surfaces3d) {
      for (const surf of data.surfaces3d) {
        const tr = surfaceTrace(surf);
        if (tr) result.push(tr);
      }
    }

    return result;
  }, [data]);

  const layout = useMemo(() => buildLayout(data.viewRange3d), [data.viewRange3d]);

  if (traces.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        3D 図示データが含まれていません。
      </p>
    );
  }

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-gray-200 bg-gray-50 p-2">
      <Plot
        data={traces}
        layout={layout}
        config={{ responsive: true, displaylogo: false, scrollZoom: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
};

export default MathGraph3D;

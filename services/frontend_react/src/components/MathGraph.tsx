import { Mafs, Coordinates, Plot, Point, Line, Text } from "mafs";
import "mafs/core.css";
import { compile } from "mathjs";
import type { PlotData, PlotCurve } from "../types/solve";

interface Props {
  data: PlotData;
}

function buildParametricFn(expr: string): ((t: number) => number) | null {
  try {
    const code = compile(expr);
    return (t: number) => code.evaluate({ t }) as number;
  } catch {
    return null;
  }
}

function ParametricCurve({
  curve,
  index,
}: {
  curve: PlotCurve;
  index: number;
}) {
  if (curve.type !== "parametric" || !curve.x || !curve.y) return null;
  const xFn = buildParametricFn(curve.x);
  const yFn = buildParametricFn(curve.y);
  if (!xFn || !yFn) return null;

  const tMin = curve.tMin ?? 0;
  const tMax = curve.tMax ?? 1;
  const colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"];
  const color = colors[index % colors.length];

  return (
    <Plot.Parametric
      xy={(t: number) => [xFn(t), yFn(t)]}
      t={[tMin, tMax]}
      color={color}
      weight={2.5}
    />
  );
}

export default function MathGraph({ data }: Props) {
  if (!data.needPlot) return null;

  const vb = data.viewBox ?? { xMin: -0.2, xMax: 1.2, yMin: -0.2, yMax: 0.85 };

  return (
    <div className="math-graph-wrapper">
      <Mafs
        viewBox={{ x: [vb.xMin, vb.xMax], y: [vb.yMin, vb.yMax] }}
        preserveAspectRatio={false}
        height={300}
      >
        <Coordinates.Cartesian />

        {/* 曲線 */}
        {data.curves.map((curve, i) => (
          <ParametricCurve key={i} curve={curve} index={i} />
        ))}

        {/* 線分 */}
        {data.segments?.map((seg, i) => (
          <Line.Segment
            key={i}
            point1={seg.from as [number, number]}
            point2={seg.to as [number, number]}
            color="#6b7280"
            weight={1.5}
          />
        ))}

        {/* 点 */}
        {data.points?.map((pt, i) => (
          <Point key={i} x={pt.x} y={pt.y} color="#dc2626" />
        ))}

        {/* ラベル */}
        {data.points
          ?.filter((pt) => pt.label)
          .map((pt, i) => (
            <Text key={i} x={pt.x + 0.04} y={pt.y + 0.04} attach="ne" size={14}>
              {pt.label!}
            </Text>
          ))}

        {/* 曲線ラベル */}
        {data.curves
          .filter((c) => c.label && c.x && c.y)
          .map((c, i) => {
            const xFn = c.x ? buildParametricFn(c.x) : null;
            const yFn = c.y ? buildParametricFn(c.y) : null;
            if (!xFn || !yFn) return null;
            const tMid = ((c.tMin ?? 0) + (c.tMax ?? 1)) / 2;
            return (
              <Text key={i} x={xFn(tMid) + 0.05} y={yFn(tMid) + 0.05} size={13}>
                {c.label!}
              </Text>
            );
          })}
      </Mafs>

      {/* 凡例 */}
      {data.curves.some((c) => c.label) && (
        <div className="math-graph-legend">
          {data.curves
            .filter((c) => c.label)
            .map((c, i) => {
              const colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"];
              return (
                <span key={i} className="legend-item">
                  <span
                    className="legend-dot"
                    style={{ background: colors[i % colors.length] }}
                  />
                  {c.label}
                </span>
              );
            })}
        </div>
      )}
    </div>
  );
}

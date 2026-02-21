import { useCallback, useEffect, useState } from "react";

interface LightboxProps {
  urls: string[];
  initialIndex?: number;
  onClose: () => void;
}

export default function Lightbox({
  urls,
  initialIndex = 0,
  onClose,
}: LightboxProps) {
  const [index, setIndex] = useState(initialIndex);

  const prev = useCallback(
    () => setIndex((i) => (i - 1 + urls.length) % urls.length),
    [urls.length],
  );
  const next = useCallback(
    () => setIndex((i) => (i + 1) % urls.length),
    [urls.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, prev, next]);

  return (
    <div className="lightbox" role="dialog" aria-modal="true">
      <div className="lightbox-backdrop" onClick={onClose} />
      <div className="lightbox-body">
        <button
          className="lightbox-close button ghost icon-only"
          onClick={onClose}
          aria-label="Close"
        >
          ✕
        </button>
        <img
          className="lightbox-image"
          src={urls[index]}
          alt={`Image ${index + 1} of ${urls.length}`}
        />
        {urls.length > 1 && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: "1rem",
              marginTop: "0.5rem",
            }}
          >
            <button
              className="button ghost icon-only"
              onClick={prev}
              aria-label="Previous"
            >
              <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <span className="muted" style={{ alignSelf: "center" }}>
              {index + 1} / {urls.length}
            </span>
            <button
              className="button ghost icon-only"
              onClick={next}
              aria-label="Next"
            >
              <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

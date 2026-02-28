import type { FC } from "react";
import type { Recommendation } from "../types/learning";

interface RecommendationCarouselProps {
  items: Recommendation[];
}

const RecommendationCarousel: FC<RecommendationCarouselProps> = ({ items }) => {
  return (
    <section className="phase3-card">
      <h3 className="phase3-title">推薦教材</h3>
      {items.length === 0 ? (
        <p className="phase3-empty">推薦結果がありません</p>
      ) : (
        <div className="phase3-recommendations">
          {items.map((item) => (
            <article key={item.material_id} className="phase3-rec-item">
              <p className="phase3-rec-id">{item.material_id}</p>
              <p className="phase3-rec-score">
                類似度: {(item.score * 100).toFixed(0)}%
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default RecommendationCarousel;

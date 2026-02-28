import type { FC } from "react";
import type { LearningProfile } from "../types/learning";

interface PersonalizationPanelProps {
  profile: LearningProfile;
}

const PersonalizationPanel: FC<PersonalizationPanelProps> = ({ profile }) => {
  return (
    <section className="phase3-card">
      <h3 className="phase3-title">学習プロファイル</h3>
      <div className="phase3-grid-2">
        <div className="phase3-kv">
          <span>推奨難易度</span>
          <strong>{profile.preferred_difficulty}</strong>
        </div>
        <div className="phase3-kv">
          <span>学習速度</span>
          <strong>{profile.learning_speed}</strong>
        </div>
        <div className="phase3-kv">
          <span>完了教材数</span>
          <strong>{profile.materials_completed}</strong>
        </div>
        <div className="phase3-kv">
          <span>重点概念</span>
          <strong>
            {profile.preferred_concepts.length > 0
              ? profile.preferred_concepts.join(", ")
              : "未分析"}
          </strong>
        </div>
      </div>
    </section>
  );
};

export default PersonalizationPanel;

import type { FC } from "react";

interface ConceptDeepDiveModalProps {
  isOpen: boolean;
  concept: string;
  explanation: string;
  onClose: () => void;
}

const ConceptDeepDiveModal: FC<ConceptDeepDiveModalProps> = ({
  isOpen,
  concept,
  explanation,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="phase3-modal-backdrop" role="dialog" aria-modal="true">
      <div className="phase3-modal-card">
        <div className="phase3-modal-header">
          <h3>概念深掘り: {concept}</h3>
          <button type="button" className="button ghost" onClick={onClose}>
            閉じる
          </button>
        </div>
        <div className="phase3-modal-body">
          <pre className="phase3-pre">{explanation}</pre>
        </div>
      </div>
    </div>
  );
};

export default ConceptDeepDiveModal;

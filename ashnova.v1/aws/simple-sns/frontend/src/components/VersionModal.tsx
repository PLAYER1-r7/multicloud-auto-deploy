import React from 'react';
import type { VersionInfo } from '../types';

interface VersionModalProps {
  isOpen: boolean;
  onClose: () => void;
  versionInfo: VersionInfo | null;
}

export const VersionModal: React.FC<VersionModalProps> = ({
  isOpen,
  onClose,
  versionInfo,
}) => {
  if (!isOpen || !versionInfo) return null;

  return (
    <div className={`modal ${isOpen ? 'show' : ''}`} onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">バージョン情報</h2>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>
        <div style={{ padding: '20px' }}>
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>
              v{versionInfo.currentVersion}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              リリース日: {versionInfo.releaseDate}
            </div>
          </div>
          
          {versionInfo.changes && versionInfo.changes.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '12px' }}>主な変更点</h3>
              <ul style={{ 
                listStyle: 'none', 
                padding: 0,
                margin: 0,
              }}>
                {versionInfo.changes.map((change, index) => (
                  <li key={index} style={{ 
                    padding: '8px 0',
                    paddingLeft: '20px',
                    position: 'relative',
                    color: 'var(--text-primary)',
                    lineHeight: '1.6',
                  }}>
                    <span style={{
                      position: 'absolute',
                      left: '0',
                      color: 'var(--text-secondary)',
                    }}>•</span>
                    {change}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '20px' }}>
            <p style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>詳細なリリースノートとバージョン履歴はGitHubをご覧ください。</p>
            <a
              href={versionInfo.releaseNotesUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-block',
                padding: '10px 20px',
                backgroundColor: '#0969da',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '6px',
                fontWeight: '500',
              }}
            >
              GitHubでバージョン履歴を見る →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

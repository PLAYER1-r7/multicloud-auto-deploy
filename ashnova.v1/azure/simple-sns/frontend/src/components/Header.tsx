import React, { useEffect } from 'react';
import { FiLogIn, FiLogOut, FiRefreshCw, FiList, FiMoon, FiSun, FiSearch } from 'react-icons/fi';
import { useLocalStorage } from 'react-use';
import clsx from 'clsx';
import { useMsalAuth } from '../hooks/useMsalAuth';

interface HeaderProps {
  isAuthenticated: boolean;
  version: string;
  onReload: () => void;
  onShowVersion: () => void;
  onToggleSearch: () => void;
  onToggleProfile: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isAuthenticated,
  version,
  onReload,
  onShowVersion,
  onToggleSearch,
  onToggleProfile,
}) => {
  const { login, logout } = useMsalAuth();
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const [theme, setTheme] = useLocalStorage<'light' | 'dark'>('theme', prefersDark ? 'dark' : 'light');

  const handleSignIn = () => {
    console.log('Login button clicked');
    login();
  };

  const handleSignOut = () => {
    console.log('Logout button clicked');
    logout();
  };

  useEffect(() => {
    // Apply theme to document
    if (theme) {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <header>
      <h1>
        Simple SNS(Azure Backend)
        {version && <span className="hint" style={{ marginLeft: '10px' }}>v{version}</span>}
      </h1>
      <div className="row">
        <span className={clsx('pill', isAuthenticated ? 'ok' : 'ng')}>
          {isAuthenticated ? 'ログイン済み' : '未ログイン'}
        </span>
        <button onClick={toggleTheme} className="secondary" title="テーマ切り替え">
          {theme === 'light' ? <FiMoon /> : <FiSun />}
        </button>
        <button onClick={onToggleSearch} className="secondary" title="検索">
          <FiSearch />
        </button>
        <button onClick={onToggleProfile} className="secondary" title="ニックネーム設定">
          👤
        </button>
        <button onClick={handleSignIn} className="secondary" title="ログイン">
          <FiLogIn />
        </button>
        <button onClick={handleSignOut} className="secondary" title="ログアウト">
          <FiLogOut />
        </button>
        <button onClick={onReload} className="secondary" title="再読み込み">
          <FiRefreshCw />
        </button>
        <button onClick={onShowVersion} className="secondary" title="バージョン履歴">
          <FiList />
        </button>
      </div>
    </header>
  );
};

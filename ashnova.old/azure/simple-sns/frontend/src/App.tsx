import React, { useEffect } from 'react';
import { MsalProvider } from '@azure/msal-react';
import { PublicClientApplication, EventType } from '@azure/msal-browser';
import { msalConfig } from './config/authConfig';
import { HomePage } from './pages/HomePage';

const msalInstance = new PublicClientApplication(msalConfig);

// MSALインスタンスの初期化
msalInstance.initialize().then(() => {
  // アカウント処理を追加
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0]);
  }

  // イベントハンドラーでアカウントを設定
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as any;
      const account = payload.account;
      msalInstance.setActiveAccount(account);
    }
  });
});

function App() {
  return (
    <MsalProvider instance={msalInstance}>
      <HomePage />
    </MsalProvider>
  );
}

export default App;

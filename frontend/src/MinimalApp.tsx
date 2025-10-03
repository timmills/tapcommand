import React from 'react';

const MinimalApp: React.FC = () => {
  return (
    <div style={{ padding: '20px', backgroundColor: '#f0f0f0', color: 'black' }}>
      <h1>🟢 Minimal SmartVenue App</h1>
      <p>This is a minimal version of the SmartVenue application.</p>
      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: 'white', border: '1px solid #ddd' }}>
        <h2>Status</h2>
        <p>✅ React is rendering</p>
        <p>✅ Component mounted successfully</p>
      </div>
    </div>
  );
};

export default MinimalApp;
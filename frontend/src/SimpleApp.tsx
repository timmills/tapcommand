import React from 'react';

const SimpleApp: React.FC = () => {
  return (
    <div style={{ padding: '40px', backgroundColor: 'lightgreen', color: 'black' }}>
      <h1>✅ React is Working!</h1>
      <p>SmartVenue Application Successfully Loaded</p>
      <div style={{ marginTop: '20px', padding: '20px', backgroundColor: 'white', border: '2px solid green' }}>
        <h2>🏷️ Tag Management Test</h2>
        <p>The Add New Tag button should now work properly.</p>
        <button style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '5px' }}>
          ➕ Test Button
        </button>
      </div>
    </div>
  );
};

export default SimpleApp;
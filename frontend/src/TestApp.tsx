import React, { useState } from 'react';
import './index.css';
import { useTags } from './hooks';

function TestApp() {
  console.log('TestApp rendering...');

  try {
    const tagsHook = useTags();
    console.log('Tags hook loaded successfully');

    return (
      <div style={{ padding: '20px', backgroundColor: '#f5f5f5', color: 'black' }}>
        <h1>🧪 Test SmartVenue App</h1>
        <p>Testing step by step...</p>
        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: 'white', border: '1px solid #ddd' }}>
          <h2>Hook Status</h2>
          <p>✅ useTags hook: {tagsHook.loading ? 'Loading...' : 'Loaded'}</p>
          <p>📊 Tags count: {tagsHook.deviceTags.length}</p>
          {tagsHook.error && <p>❌ Error: {tagsHook.error}</p>}
        </div>
      </div>
    );
  } catch (error) {
    console.error('Error in TestApp:', error);
    return (
      <div style={{ padding: '20px', backgroundColor: '#ffeeee', color: 'red' }}>
        <h1>❌ Error in TestApp</h1>
        <p>Error: {error instanceof Error ? error.message : 'Unknown error'}</p>
      </div>
    );
  }
}

export default TestApp;
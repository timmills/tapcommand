import React, { useState } from 'react';
import './index.css';
import { useTags } from './hooks';

function WorkingApp() {
  console.log('WorkingApp rendering...');

  const [currentPage, setCurrentPage] = useState<'devices' | 'ir-senders' | 'yaml-builder' | 'settings'>('devices');

  try {
    const tagsHook = useTags();

    return (
      <div className="container">
        {/* Header with Navigation */}
        <div className="header">
          <div>
            <h1>🏢 SmartVenue</h1>
            <p>IR Device Control System</p>
          </div>
          <div className="nav-tabs">
            <button
              className={`nav-tab ${currentPage === 'devices' ? 'active' : ''}`}
              onClick={() => setCurrentPage('devices')}
            >
              📺 Devices (0)
            </button>
            <button
              className={`nav-tab ${currentPage === 'ir-senders' ? 'active' : ''}`}
              onClick={() => setCurrentPage('ir-senders')}
            >
              📡 IR Senders (0)
            </button>
            <button
              className={`nav-tab ${currentPage === 'yaml-builder' ? 'active' : ''}`}
              onClick={() => setCurrentPage('yaml-builder')}
            >
              🛠️ YAML Builder
            </button>
            <button
              className={`nav-tab ${currentPage === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentPage('settings')}
            >
              ⚙️ Settings
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content">
          {currentPage === 'devices' && (
            <div style={{ padding: '20px', backgroundColor: '#f5f5f5' }}>
              <h2>Devices Page</h2>
              <p>This is the devices page content.</p>
              <p>Tags loaded: {tagsHook.deviceTags.length}</p>
            </div>
          )}

          {currentPage === 'ir-senders' && (
            <div style={{ padding: '20px', backgroundColor: '#f0f8ff' }}>
              <h2>IR Senders Page</h2>
              <p>This is the IR senders page content.</p>
            </div>
          )}

          {currentPage === 'yaml-builder' && (
            <div style={{ padding: '20px', backgroundColor: '#fff8f0' }}>
              <h2>YAML Builder Page</h2>
              <p>This is the YAML builder page content.</p>
            </div>
          )}

          {currentPage === 'settings' && (
            <div style={{ padding: '20px', backgroundColor: '#f8f0ff' }}>
              <h2>Settings Page</h2>
              <p>This is the settings page content.</p>
            </div>
          )}
        </div>
      </div>
    );
  } catch (error) {
    console.error('Error in WorkingApp:', error);
    return (
      <div style={{ padding: '20px', backgroundColor: '#ffeeee', color: 'red' }}>
        <h1>❌ Error in WorkingApp</h1>
        <p>Error: {error instanceof Error ? error.message : 'Unknown error'}</p>
      </div>
    );
  }
}

export default WorkingApp;
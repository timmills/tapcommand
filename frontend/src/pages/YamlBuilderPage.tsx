import React, { useRef } from 'react';
import type { TemplateCategory, SelectedLibrary } from '../types';
import { copyTextToClipboard } from '../utils';

interface YamlBuilderPageProps {
  builderError: string | null;
  builderLoading: boolean;
  templateCategories: TemplateCategory[];
  selectedLibraries: SelectedLibrary[];
  portAssignments: (number | null)[];
  yamlPreview: string;
  yamlCharCount: number;
  baseTemplate: string;
  includeComments: boolean;
  previewLoading: boolean;
  compileOutput: string | null;
  compileLoading: boolean;
  downloadUrl: string | null;
  binaryFilename: string | null;
  setBuilderError: (error: string | null) => void;
  setIncludeComments: (include: boolean) => void;
  handleSelectLibrary: (library: SelectedLibrary) => void;
  handleRemoveLibrary: (libraryId: number) => void;
  handlePortAssignmentChange: (portIndex: number, value: string) => void;
  handleSaveYaml: () => void;
  handleSaveYamlToServer: () => void;
  handleCompile: () => void;
  compileOutputRef: React.RefObject<HTMLPreElement>;
}

const YamlBuilderPage: React.FC<YamlBuilderPageProps> = ({
  builderError,
  builderLoading,
  templateCategories,
  selectedLibraries,
  portAssignments,
  yamlPreview,
  yamlCharCount,
  baseTemplate,
  includeComments,
  previewLoading,
  compileOutput,
  compileLoading,
  downloadUrl,
  binaryFilename,
  setBuilderError,
  setIncludeComments,
  handleSelectLibrary,
  handleRemoveLibrary,
  handlePortAssignmentChange,
  handleSaveYaml,
  handleSaveYamlToServer,
  handleCompile,
  compileOutputRef
}) => {
  return (
    <div className="yaml-builder-page">
      <div className="page-header">
        <h2>🧪 ESPHome YAML Builder</h2>
        <p>Craft D1 Mini firmware templates by pairing SmartVenue ports with IR libraries.</p>
      </div>

      {builderError && (
        <div className="builder-error">⚠️ {builderError}</div>
      )}

      {builderLoading && (
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="loading">Preparing template workspace...</div>
        </div>
      )}

      {!builderLoading && (
        <div className="builder-content">
          <div className="builder-left">
            <div className="card hierarchy-card">
              <div className="card-header">
                <h3>Device Library</h3>
                <p>Select up to two device profiles to include in this build.</p>
              </div>
              <div className="hierarchy-scroll">
                {templateCategories.length === 0 ? (
                  <div className="empty-state">No IR libraries available yet.</div>
                ) : (
                  templateCategories.map((category) => (
                    <details key={category.name} className="hierarchy-category" open>
                      <summary>{category.name}</summary>
                      {category.brands.map((brand) => (
                        <details key={`${category.name}-${brand.name}`} className="hierarchy-brand">
                          <summary>{brand.name}</summary>
                          <ul>
                            {brand.libraries.map((library) => {
                              const alreadySelected = selectedLibraries.some((item) => item.id === library.id);
                              return (
                                <li key={library.id}>
                                  <button
                                    className="hierarchy-select"
                                    onClick={() => handleSelectLibrary(library)}
                                    disabled={alreadySelected || selectedLibraries.length >= 2}
                                  >
                                    ➕ {library.name}
                                    {library.model ? ` (${library.model})` : ''}
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        </details>
                      ))}
                    </details>
                  ))
                )}
              </div>
            </div>

            <div className="card selected-card">
              <div className="card-header">
                <h3>Selected Devices ({selectedLibraries.length}/2)</h3>
              </div>
              {selectedLibraries.length === 0 ? (
                <p className="muted">Pick up to two IR libraries to assign across the five ports.</p>
              ) : (
                <ul className="selected-list">
                  {selectedLibraries.map((library) => (
                    <li key={library.id}>
                      <div>
                        <div className="selected-name">{library.name}</div>
                        <div className="selected-meta">{library.brand} • {library.device_category}</div>
                      </div>
                      <button className="button secondary" onClick={() => handleRemoveLibrary(library.id)}>
                        ✖ Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card mapping-card">
              <div className="card-header">
                <h3>Port Mapping</h3>
                <p>Assign each SmartVenue IR port to a selected device.</p>
              </div>
              <table className="port-table">
                <thead>
                  <tr>
                    <th>Port</th>
                    <th>Device</th>
                  </tr>
                </thead>
                <tbody>
                  {portAssignments.map((assignment, index) => (
                    <tr key={index}>
                      <td>Port {index + 1}</td>
                      <td>
                        <select
                          value={assignment ?? ''}
                          onChange={(e) => handlePortAssignmentChange(index, e.target.value)}
                        >
                          <option value="">Unused</option>
                          {selectedLibraries.map((library) => (
                            <option key={library.id} value={library.id}>
                              {library.name}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="builder-right">
            <div className="card preview-card">
              <div className="preview-header">
                <div className="char-count">Character Count: {yamlPreview ? yamlCharCount : baseTemplate.length}</div>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={includeComments}
                    onChange={(e) => setIncludeComments(e.target.checked)}
                  />
                  Include Comments
                </label>
                <button
                  className="button secondary"
                  style={{ marginLeft: 'auto' }}
                  onClick={async () => {
                    const text = (yamlPreview || baseTemplate || '').trim();
                    if (!text) {
                      return;
                    }
                    const success = await copyTextToClipboard(text);
                    if (!success) {
                      setBuilderError('Failed to copy YAML to clipboard.');
                    }
                  }}
                >
                  📋 Copy YAML
                </button>
                <button
                  className="button"
                  style={{ marginLeft: '8px' }}
                  onClick={handleSaveYaml}
                >
                  💾 Download YAML
                </button>
                <button
                  className="button"
                  style={{ marginLeft: '8px' }}
                  onClick={handleSaveYamlToServer}
                >
                  🌐 Save to Server
                </button>
                <button
                  className="button"
                  style={{ marginLeft: '8px' }}
                  onClick={handleCompile}
                  disabled={compileLoading}
                >
                  {compileLoading ? 'Compiling…' : '⚙️ Compile'}
                </button>
              </div>
              {previewLoading && <div className="preview-loading">Rendering preview...</div>}
              <pre className="yaml-preview">{(yamlPreview || baseTemplate || '# Template loading...')}</pre>
              {compileOutput && (
                <details className="compile-output" open>
                  <summary>
                    Compilation Output
                    {downloadUrl && binaryFilename && (
                      <a
                        href={downloadUrl}
                        download={binaryFilename}
                        className="download-btn"
                        style={{ marginLeft: '12px', fontSize: '14px' }}
                      >
                        📦 Download {binaryFilename}
                      </a>
                    )}
                  </summary>
                  <pre ref={compileOutputRef}>{compileOutput}</pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default YamlBuilderPage;
import React from 'react';
import type { DeviceTag } from '../types';

interface TagManagementTabProps {
  settingsLoading: boolean;
  deviceTags: DeviceTag[];
  editingTag: DeviceTag | null;
  setEditingTag: (tag: DeviceTag | null) => void;
  handleTagDelete: (tagId: number) => Promise<void>;
  handleTagSave: (e: React.FormEvent) => Promise<void>;
}

const TagManagementTab: React.FC<TagManagementTabProps> = ({
  settingsLoading,
  deviceTags,
  editingTag,
  setEditingTag,
  handleTagDelete,
  handleTagSave
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <h3>🏷️ Device Tags</h3>
        <p>Create and manage tags for organizing your devices</p>
        <button
          className="button"
          onClick={() => setEditingTag({ id: 0, name: '', color: '#3b82f6', description: '', usage_count: 0, created_at: '', updated_at: '' })}
        >
          ➕ Add New Tag
        </button>
      </div>

      {settingsLoading ? (
        <div className="loading">Loading tags...</div>
      ) : deviceTags.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🏷️</div>
          <h3>No Tags Yet</h3>
          <p>Create tags to organize and group your devices for easier management.</p>
        </div>
      ) : (
        <div className="tags-display">
          <div className="tags-container">
            {deviceTags.map(tag => (
              <div key={tag.id} className="interactive-tag-wrapper">
                <div
                  className="interactive-tag"
                  style={{
                    backgroundColor: tag.color || '#6b7280',
                    color: '#ffffff'
                  }}
                  onClick={() => setEditingTag(tag)}
                  title={`Click to edit "${tag.name}"`}
                >
                  <span className="tag-name">{tag.name}</span>
                  <span className="tag-count">({tag.usage_count})</span>
                </div>
                <button
                  className="tag-delete-btn"
                  onClick={() => handleTagDelete(tag.id)}
                  title={`Delete "${tag.name}" tag`}
                  disabled={tag.usage_count > 0}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div style={{ marginTop: '16px', fontSize: '14px', color: '#6b7280' }}>
            Click on a tag to edit it. Tags in use cannot be deleted.
          </div>
        </div>
      )}

      {/* Tag Edit Modal */}
      {editingTag && (
        <div className="modal-overlay" onClick={() => setEditingTag(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <form onSubmit={handleTagSave}>
              <div className="modal-header">
                <h3>{editingTag.id === 0 ? 'Create' : 'Edit'} Tag</h3>
              </div>

              <div className="modal-body">
                <div className="form-group">
                  <label>Tag Name</label>
                  <input
                    type="text"
                    value={editingTag.name}
                    onChange={(e) => setEditingTag({
                      ...editingTag,
                      name: e.target.value
                    })}
                    placeholder="Enter tag name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Color</label>
                  <input
                    type="color"
                    value={editingTag.color}
                    onChange={(e) => setEditingTag({
                      ...editingTag,
                      color: e.target.value
                    })}
                  />
                </div>

                <div className="form-group">
                  <label>Description (Optional)</label>
                  <textarea
                    value={editingTag.description || ''}
                    onChange={(e) => setEditingTag({
                      ...editingTag,
                      description: e.target.value
                    })}
                    placeholder="Optional description for this tag"
                    rows={3}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setEditingTag(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="button">
                  {editingTag.id === 0 ? 'Create Tag' : 'Update Tag'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TagManagementTab;
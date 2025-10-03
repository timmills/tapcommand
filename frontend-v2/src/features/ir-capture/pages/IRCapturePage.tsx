/**
 * IR Remote Code Capture Page - MVP Version
 *
 * Simple workflow:
 * 1. Create capture session
 * 2. User manually pastes codes from ESP logs
 * 3. Save codes to session
 * 4. Create remote profile from session
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';

import {
  createCaptureSession,
  listCaptureSessions,
  addCodeToSession,
  listSessionCodes,
  deleteCode,
  createCapturedRemote,
  completeSession,
  getLastCapturedCode,
} from '../api/ir-capture-api';
import type {
  CreateSessionRequest,
  AddCodeRequest,
  CaptureSession,
  CapturedCode,
} from '../../../types/ir-capture';

type ViewMode = 'sessions' | 'capture' | 'complete';

export const IRCapturePage = () => {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>('sessions');
  const [activeSession, setActiveSession] = useState<CaptureSession | null>(null);

  // Query: List sessions
  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ['capture-sessions'],
    queryFn: () => listCaptureSessions(),
  });

  // Query: List codes for active session
  const { data: codes = [], isLoading: codesLoading } = useQuery({
    queryKey: ['session-codes', activeSession?.id],
    queryFn: () => listSessionCodes(activeSession!.id),
    enabled: !!activeSession,
  });

  // Mutation: Create session
  const createSessionMutation = useMutation({
    mutationFn: createCaptureSession,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] });
      setActiveSession(session);
      setViewMode('capture');
    },
  });

  // Mutation: Add code
  const addCodeMutation = useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: number; data: AddCodeRequest }) =>
      addCodeToSession(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session-codes', activeSession?.id] });
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] });
    },
  });

  // Mutation: Delete code
  const deleteCodeMutation = useMutation({
    mutationFn: ({ sessionId, codeId }: { sessionId: number; codeId: number }) =>
      deleteCode(sessionId, codeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session-codes', activeSession?.id] });
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] });
    },
  });

  // Mutation: Complete session & create remote
  const completeSessionMutation = useMutation({
    mutationFn: async ({ sessionId, remoteName }: { sessionId: number; remoteName: string }) => {
      await completeSession(sessionId);
      return createCapturedRemote({
        session_id: sessionId,
        name: remoteName,
        is_favorite: false,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] });
      setActiveSession(null);
      setViewMode('sessions');
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">IR Code Capture</h1>
          <p className="text-sm text-gray-600 mt-1">
            Capture IR codes from remote controls and create custom remote profiles
          </p>
        </div>
        {viewMode !== 'sessions' && (
          <button
            onClick={() => {
              setActiveSession(null);
              setViewMode('sessions');
            }}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Back to Sessions
          </button>
        )}
      </div>

      {viewMode === 'sessions' && (
        <SessionsView
          sessions={sessions}
          loading={sessionsLoading}
          onCreateSession={(data) => createSessionMutation.mutate(data)}
          onSelectSession={(session) => {
            setActiveSession(session);
            setViewMode('capture');
          }}
          creating={createSessionMutation.isPending}
        />
      )}

      {viewMode === 'capture' && activeSession && (
        <CaptureView
          session={activeSession}
          codes={codes}
          loading={codesLoading}
          onAddCode={(data) =>
            addCodeMutation.mutate({ sessionId: activeSession.id, data })
          }
          onDeleteCode={(codeId) =>
            deleteCodeMutation.mutate({ sessionId: activeSession.id, codeId })
          }
          onComplete={() => setViewMode('complete')}
          adding={addCodeMutation.isPending}
          deleting={deleteCodeMutation.isPending}
        />
      )}

      {viewMode === 'complete' && activeSession && (
        <CompleteView
          session={activeSession}
          codeCount={codes.length}
          onComplete={(remoteName) =>
            completeSessionMutation.mutate({ sessionId: activeSession.id, remoteName })
          }
          onBack={() => setViewMode('capture')}
          completing={completeSessionMutation.isPending}
        />
      )}
    </div>
  );
};

// ==================== SESSIONS VIEW ====================

interface SessionsViewProps {
  sessions: CaptureSession[];
  loading: boolean;
  onCreateSession: (data: CreateSessionRequest) => void;
  onSelectSession: (session: CaptureSession) => void;
  creating: boolean;
}

const SessionsView = ({
  sessions,
  loading,
  onCreateSession,
  onSelectSession,
  creating,
}: SessionsViewProps) => {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<CreateSessionRequest>({
    session_name: '',
    device_type: 'TV',
    brand: '',
    model: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreateSession(formData);
    setShowForm(false);
    setFormData({ session_name: '', device_type: 'TV', brand: '', model: '' });
  };

  const activeSessions = sessions.filter((s) => s.status === 'active');
  const completedSessions = sessions.filter((s) => s.status === 'completed');

  return (
    <div className="space-y-6">
      {/* Create Session Button */}
      <div className="flex justify-end">
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
        >
          New Capture Session
        </button>
      </div>

      {/* Create Session Form */}
      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Capture Session</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Remote Name *
              </label>
              <input
                type="text"
                required
                value={formData.session_name}
                onChange={(e) => setFormData({ ...formData, session_name: e.target.value })}
                placeholder="e.g., Living Room TV"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Device Type
                </label>
                <select
                  value={formData.device_type}
                  onChange={(e) => setFormData({ ...formData, device_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="TV">TV</option>
                  <option value="Projector">Projector</option>
                  <option value="AC">Air Conditioner</option>
                  <option value="Audio">Audio System</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Brand (optional)
                </label>
                <input
                  type="text"
                  value={formData.brand}
                  onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                  placeholder="e.g., Samsung"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model (optional)
                </label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  placeholder="e.g., UN55RU7100"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create Session'}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Active Sessions */}
      {activeSessions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Active Sessions</h3>
          <div className="grid gap-3">
            {activeSessions.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                onClick={() => onSelectSession(session)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Completed Sessions */}
      {completedSessions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Completed Sessions</h3>
          <div className="grid gap-3">
            {completedSessions.map((session) => (
              <SessionCard
                key={session.id}
                session={session}
                onClick={() => onSelectSession(session)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && sessions.length === 0 && !showForm && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <p className="text-gray-600 mb-4">No capture sessions yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            Create Your First Session
          </button>
        </div>
      )}
    </div>
  );
};

const SessionCard = ({
  session,
  onClick,
}: {
  session: CaptureSession;
  onClick: () => void;
}) => {
  return (
    <button
      onClick={onClick}
      className="w-full bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-500 hover:shadow-md transition-all text-left"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">{session.session_name}</h4>
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
            <span>{session.device_type}</span>
            {session.brand && <span>• {session.brand}</span>}
            {session.model && <span>• {session.model}</span>}
          </div>
          <div className="mt-2 text-sm text-gray-500">
            {session.code_count} {session.code_count === 1 ? 'code' : 'codes'} captured
          </div>
        </div>
        <div
          className={clsx(
            'px-2 py-1 text-xs font-medium rounded',
            session.status === 'active' && 'bg-green-100 text-green-800',
            session.status === 'completed' && 'bg-blue-100 text-blue-800',
            session.status === 'cancelled' && 'bg-gray-100 text-gray-800'
          )}
        >
          {session.status}
        </div>
      </div>
    </button>
  );
};

// ==================== CAPTURE VIEW ====================

interface CaptureViewProps {
  session: CaptureSession;
  codes: CapturedCode[];
  loading: boolean;
  onAddCode: (data: AddCodeRequest) => void;
  onDeleteCode: (codeId: number) => void;
  onComplete: () => void;
  adding: boolean;
  deleting: boolean;
}

const CaptureView = ({
  session,
  codes,
  loading,
  onAddCode,
  onDeleteCode,
  onComplete,
  adding,
}: CaptureViewProps) => {
  const [formData, setFormData] = useState<AddCodeRequest>({
    button_name: '',
    button_category: '',
    protocol: 'RAW',
    raw_data: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAddCode(formData);
    setFormData({
      button_name: '',
      button_category: '',
      protocol: 'RAW',
      raw_data: '',
    });
  };

  return (
    <div className="space-y-6">
      {/* Session Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900">{session.session_name}</h3>
        <p className="text-sm text-blue-700 mt-1">
          {session.device_type}
          {session.brand && ` • ${session.brand}`}
          {session.model && ` • ${session.model}`}
        </p>
        <p className="text-sm text-blue-600 mt-2">
          {codes.length} {codes.length === 1 ? 'code' : 'codes'} captured
        </p>
      </div>

      {/* Device Status & Instructions */}
      <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-2">🎯 Quick Capture Guide:</h4>
        <ol className="list-decimal list-inside space-y-1 text-sm text-gray-700 mb-3">
          <li>Point your remote at the IR receiver (connected to the ESP32 device)</li>
          <li>Press the button you want to capture</li>
          <li>Click the "🔄 Fetch from Device" button below to auto-fill the code</li>
          <li>Name the button and add it to your session</li>
          <li>Repeat for all buttons you want to capture</li>
        </ol>
        <div className="flex items-center gap-2 text-xs text-gray-600 bg-white bg-opacity-70 px-3 py-2 rounded">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span>ESP32 IR Capture Device @ 192.168.101.126</span>
        </div>
      </div>

      {/* Add Code Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Add IR Code</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Button Name *
              </label>
              <input
                type="text"
                required
                value={formData.button_name}
                onChange={(e) => setFormData({ ...formData, button_name: e.target.value })}
                placeholder="e.g., Power, Volume Up, Channel 1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category (optional)
              </label>
              <select
                value={formData.button_category}
                onChange={(e) => setFormData({ ...formData, button_category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Not specified</option>
                <option value="power">Power</option>
                <option value="volume">Volume</option>
                <option value="channel">Channel</option>
                <option value="number">Number</option>
                <option value="menu">Menu</option>
                <option value="navigation">Navigation</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                Raw Timing Data *
              </label>
              <button
                type="button"
                onClick={async () => {
                  try {
                    const response = await getLastCapturedCode();
                    if (response.success && response.raw_data) {
                      setFormData({ ...formData, raw_data: response.raw_data });
                    }
                  } catch (error) {
                    console.error('Failed to fetch code:', error);
                  }
                }}
                className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
              >
                🔄 Fetch from Device
              </button>
            </div>
            <textarea
              required
              value={formData.raw_data}
              onChange={(e) => setFormData({ ...formData, raw_data: e.target.value })}
              placeholder="Paste raw IR data from logs, e.g.: 4500, 4500, 560, 1690, 560, 560, ..."
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Supports both comma-separated values and JSON array format
            </p>
          </div>

          <button
            type="submit"
            disabled={adding}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {adding ? 'Adding...' : 'Add Code'}
          </button>
        </form>
      </div>

      {/* Captured Codes List */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Captured Codes</h3>
          {codes.length > 0 && (
            <button
              onClick={onComplete}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700"
            >
              Complete & Create Remote
            </button>
          )}
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading codes...</div>
        ) : codes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No codes captured yet. Add your first code above.
          </div>
        ) : (
          <div className="space-y-2">
            {codes.map((code) => (
              <div
                key={code.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{code.button_name}</div>
                  <div className="text-sm text-gray-600">
                    {code.button_category && (
                      <span className="capitalize">{code.button_category} • </span>
                    )}
                    <span>{code.protocol}</span>
                  </div>
                </div>
                <button
                  onClick={() => onDeleteCode(code.id)}
                  className="px-3 py-1 text-sm font-medium text-red-600 hover:bg-red-50 rounded"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== COMPLETE VIEW ====================

interface CompleteViewProps {
  session: CaptureSession;
  codeCount: number;
  onComplete: (remoteName: string) => void;
  onBack: () => void;
  completing: boolean;
}

const CompleteView = ({
  session,
  codeCount,
  onComplete,
  onBack,
  completing,
}: CompleteViewProps) => {
  const [remoteName, setRemoteName] = useState(session.session_name);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onComplete(remoteName);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white border border-gray-200 rounded-lg p-8 shadow-sm">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Capture Complete!</h3>
          <p className="text-gray-600">
            You've successfully captured {codeCount} IR{' '}
            {codeCount === 1 ? 'code' : 'codes'} from your remote control.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Remote Profile Name
            </label>
            <input
              type="text"
              required
              value={remoteName}
              onChange={(e) => setRemoteName(e.target.value)}
              placeholder="e.g., Living Room TV Remote"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-sm text-gray-500 mt-1">
              This will create a reusable remote profile you can use anywhere
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-semibold text-blue-900 mb-2">What happens next?</h4>
            <ul className="space-y-1 text-sm text-blue-700">
              <li>• Your capture session will be marked as completed</li>
              <li>• A custom remote profile will be created with all {codeCount} buttons</li>
              <li>• You can use this remote to control devices from the control page</li>
              <li>• The remote will appear in your custom remotes library</li>
            </ul>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={completing}
              className="flex-1 px-6 py-3 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {completing ? 'Creating Remote...' : 'Create Remote Profile'}
            </button>
            <button
              type="button"
              onClick={onBack}
              className="px-6 py-3 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Back
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

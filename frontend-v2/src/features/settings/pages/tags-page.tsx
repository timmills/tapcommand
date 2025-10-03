import { useMemo, useState } from 'react';
import {
  useDeviceTags,
  useCreateDeviceTag,
  useUpdateDeviceTag,
  useDeleteDeviceTag,
} from '../hooks/use-device-tags';
import type { DeviceTag } from '@/types';

export const TagsPage = () => {
  const { data: tags = [], isLoading, error } = useDeviceTags();
  const createMutation = useCreateDeviceTag();
  const updateMutation = useUpdateDeviceTag();
  const deleteMutation = useDeleteDeviceTag();

  const [createForm, setCreateForm] = useState({ name: '', color: '#2563ff', description: '' });
  const [createError, setCreateError] = useState<string | null>(null);

  const [editingTagId, setEditingTagId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: '', color: '#2563ff', description: '' });
  const [editError, setEditError] = useState<string | null>(null);

  const sortedTags = useMemo(
    () => tags.slice().sort((a, b) => a.name.localeCompare(b.name)),
    [tags],
  );

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreateError(null);

    const payload = {
      name: createForm.name.trim(),
      color: createForm.color || null,
      description: createForm.description.trim() ? createForm.description.trim() : null,
    };

    if (!payload.name) {
      setCreateError('Tag name is required.');
      return;
    }

    try {
      await createMutation.mutateAsync(payload);
      setCreateForm({ name: '', color: '#2563ff', description: '' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to create tag.';
      setCreateError(message);
    }
  };

  const beginEdit = (tag: DeviceTag) => {
    setEditingTagId(tag.id);
    setEditForm({
      name: tag.name,
      color: tag.color ?? '#2563ff',
      description: tag.description ?? '',
    });
    setEditError(null);
  };

  const cancelEdit = () => {
    setEditingTagId(null);
    setEditError(null);
  };

  const handleUpdate = async () => {
    if (editingTagId === null) return;

    const payload = {
      name: editForm.name.trim(),
      color: editForm.color || null,
      description: editForm.description.trim() ? editForm.description.trim() : null,
    };

    if (!payload.name) {
      setEditError('Tag name is required.');
      return;
    }

    try {
      await updateMutation.mutateAsync({ id: editingTagId, payload });
      setEditingTagId(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to update tag.';
      setEditError(message);
    }
  };

  const handleDelete = async (tag: DeviceTag) => {
    if (deleteMutation.isPending) return;
    const confirmed = window.confirm(
      `Delete the "${tag.name}" tag? It will be removed from every controller port.`,
    );
    if (!confirmed) return;

    try {
      await deleteMutation.mutateAsync(tag.id);
      if (editingTagId === tag.id) {
        setEditingTagId(null);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to delete tag.';
      setEditError(message);
    }
  };

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Device Tags</h2>
        <p className="text-sm text-slate-500">
          Create and manage tags to organize and group your devices for scheduling and bulk operations.
        </p>
      </header>

      <form onSubmit={handleCreate} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Create a new tag</h3>
        <div className="mt-3 grid gap-4 md:grid-cols-3">
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Tag name
            <input
              type="text"
              value={createForm.name}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, name: event.target.value }))}
              className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. Sports, Lounge TV"
            />
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Color
            <input
              type="color"
              value={createForm.color}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, color: event.target.value }))}
              className="mt-1 h-10 w-full cursor-pointer rounded-md border border-slate-300 bg-white"
            />
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-600 md:col-span-1 md:col-start-1 md:row-start-2">
            Description
            <input
              type="text"
              value={createForm.description}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, description: event.target.value }))}
              className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="Optional context"
            />
          </label>
        </div>
        {createError ? <p className="mt-2 text-xs text-rose-600">{createError}</p> : null}
        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="inline-flex items-center rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
          >
            {createMutation.isPending ? 'Creating…' : 'Add tag'}
          </button>
        </div>
      </form>

      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">Existing tags</h3>
          {isLoading ? <span className="text-xs text-slate-500">Loading…</span> : null}
        </div>
        {error ? (
          <div className="p-4 text-sm text-rose-600">Failed to load tags: {error.message}</div>
        ) : sortedTags.length === 0 ? (
          <div className="p-4 text-sm text-slate-500">No tags defined yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2 text-left">Tag</th>
                  <th className="px-4 py-2 text-left">Usage</th>
                  <th className="px-4 py-2 text-left">Description</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {sortedTags.map((tag) => {
                  const isEditing = editingTagId === tag.id;
                  return (
                    <tr key={tag.id} className="align-top">
                      <td className="px-4 py-2">
                        {isEditing ? (
                          <div className="flex flex-col gap-2">
                            <input
                              type="text"
                              value={editForm.name}
                              onChange={(event) => setEditForm((prev) => ({ ...prev, name: event.target.value }))}
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                            />
                            <div className="flex items-center gap-2">
                              <input
                                type="color"
                                value={editForm.color}
                                onChange={(event) => setEditForm((prev) => ({ ...prev, color: event.target.value }))}
                                className="h-9 w-16 cursor-pointer rounded-md border border-slate-300 bg-white"
                              />
                              <span className="text-xs text-slate-500">Colour</span>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-3">
                            <span
                              className="h-3 w-3 rounded-full"
                              style={{ backgroundColor: tag.color ?? '#64748b' }}
                              aria-hidden="true"
                            />
                            <span className="font-medium text-slate-900">{tag.name}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-2 text-slate-600">{tag.usage_count}</td>
                      <td className="px-4 py-2 text-slate-600">
                        {isEditing ? (
                          <textarea
                            value={editForm.description}
                            onChange={(event) =>
                              setEditForm((prev) => ({ ...prev, description: event.target.value }))
                            }
                            rows={2}
                            className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                          />
                        ) : tag.description ? (
                          tag.description
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {isEditing ? (
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={cancelEdit}
                              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={handleUpdate}
                              disabled={updateMutation.isPending}
                              className="rounded-md bg-brand-500 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
                            >
                              {updateMutation.isPending ? 'Saving…' : 'Save'}
                            </button>
                          </div>
                        ) : (
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => beginEdit(tag)}
                              className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDelete(tag)}
                              className="rounded-md border border-rose-200 px-3 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {editError ? <p className="px-4 pb-4 text-xs text-rose-600">{editError}</p> : null}
      </div>
    </section>
  );
};

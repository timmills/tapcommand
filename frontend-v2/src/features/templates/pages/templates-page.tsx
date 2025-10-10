import { useState } from 'react';
import { useTemplateSummaries } from '../hooks/use-template-summaries';
import { TemplateDetail } from '../components/template-detail';

export const TemplatesPage = () => {
  const { data, isLoading, isError, error } = useTemplateSummaries();
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">IR Controller Builder</h2>
          <p className="text-sm text-slate-500">
            Browse and manage TapCommand IR controller templates before compiling new firmware builds.
          </p>
        </div>
      </header>

      {isLoading ? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading templates…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load template summaries. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {(data ?? []).map((template) => {
            const isSelected = selectedTemplateId === template.id;
            return (
              <button
                key={template.id}
                type="button"
                onClick={() => setSelectedTemplateId(template.id)}
                className={`rounded-lg border p-4 text-left shadow-sm transition ${
                  isSelected
                    ? 'border-brand-400 bg-brand-50'
                    : 'border-slate-200 bg-white hover:border-brand-200 hover:shadow'
                }`}
              >
                <div className="text-sm font-semibold text-slate-900">{template.name}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {template.board} • v{template.version} (rev {template.revision})
                </div>
                {template.description && (
                  <p className="mt-2 overflow-hidden text-ellipsis whitespace-nowrap text-sm text-slate-600">
                    {template.description}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      )}

      {selectedTemplateId && <TemplateDetail templateId={selectedTemplateId} />}
    </section>
  );
};

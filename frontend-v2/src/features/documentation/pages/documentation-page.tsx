import { useState, useMemo } from 'react';
import { FileText, Search, Calendar, HardDrive } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { useDocumentationFiles, useDocumentationContent } from '../hooks/use-documentation';

export function DocumentationPage() {
  const { data: files, isLoading, isError } = useDocumentationFiles();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { data: content, isLoading: isLoadingContent } = useDocumentationContent(selectedFile);

  // Group files by category
  const groupedFiles = useMemo(() => {
    if (!files) return {};

    const groups: Record<string, typeof files> = {};
    files.forEach((file) => {
      if (!groups[file.category]) {
        groups[file.category] = [];
      }
      groups[file.category].push(file);
    });

    return groups;
  }, [files]);

  // Filter files by search term
  const filteredGroups = useMemo(() => {
    if (!searchTerm) return groupedFiles;

    const filtered: Record<string, typeof files> = {};
    Object.entries(groupedFiles).forEach(([category, categoryFiles]) => {
      const matchingFiles = categoryFiles.filter(
        (file) =>
          file.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          file.filename.toLowerCase().includes(searchTerm.toLowerCase())
      );
      if (matchingFiles.length > 0) {
        filtered[category] = matchingFiles;
      }
    });

    return filtered;
  }, [groupedFiles, searchTerm]);

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Format date
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <section className="space-y-6">
      {/* Page header */}
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Documentation</h2>
        <p className="text-sm text-slate-500">Browse system documentation and guides</p>
      </header>

      <div className="flex gap-6">
        {/* Sidebar - File list */}
        <div className="w-80 flex-shrink-0 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search documentation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-md border border-slate-300 pl-10 pr-4 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-center text-sm text-slate-500">
              Loading documentation...
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              Failed to load documentation files
            </div>
          )}

          {/* File list */}
          {!isLoading && !isError && (
            <div className="space-y-4 rounded-lg border border-slate-200 bg-white">
              {Object.keys(filteredGroups).length === 0 && (
                <div className="p-8 text-center text-sm text-slate-500">
                  {searchTerm ? 'No documentation matches your search' : 'No documentation files found'}
                </div>
              )}

              {Object.entries(filteredGroups).map(([category, categoryFiles]) => (
                <div key={category} className="border-b border-slate-100 last:border-b-0">
                  <div className="bg-slate-50 px-4 py-2">
                    <h3 className="text-xs font-semibold uppercase text-slate-600">{category}</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {categoryFiles?.map((file) => (
                      <button
                        key={file.path}
                        onClick={() => setSelectedFile(file.path)}
                        className={`w-full px-4 py-3 text-left transition hover:bg-slate-50 ${
                          selectedFile === file.path ? 'bg-brand-50' : ''
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <FileText
                            className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                              selectedFile === file.path ? 'text-brand-600' : 'text-slate-400'
                            }`}
                          />
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-sm font-medium ${
                                selectedFile === file.path ? 'text-brand-900' : 'text-slate-900'
                              }`}
                            >
                              {file.title}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">{formatFileSize(file.size)}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Main content area */}
        <div className="flex-1 min-w-0">
          {!selectedFile && (
            <div className="flex h-96 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white">
              <div className="text-center">
                <FileText className="mx-auto h-12 w-12 text-slate-300" />
                <h3 className="mt-2 text-sm font-medium text-slate-900">No document selected</h3>
                <p className="mt-1 text-sm text-slate-500">Choose a document from the list to view its contents</p>
              </div>
            </div>
          )}

          {selectedFile && isLoadingContent && (
            <div className="flex h-96 items-center justify-center rounded-lg border border-slate-200 bg-white">
              <div className="text-center text-sm text-slate-500">Loading document...</div>
            </div>
          )}

          {selectedFile && content && (
            <div className="rounded-lg border border-slate-200 bg-white">
              {/* Document header */}
              <div className="border-b border-slate-200 px-6 py-4">
                <h3 className="text-lg font-semibold text-slate-900">{content.filename.replace('.md', '')}</h3>
                <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    {formatDate(content.modified)}
                  </div>
                  <div className="flex items-center gap-1">
                    <HardDrive className="h-3.5 w-3.5" />
                    {formatFileSize(content.size)}
                  </div>
                </div>
              </div>

              {/* Markdown content */}
              <div className="prose prose-slate max-w-none px-6 py-6">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw, rehypeSanitize]}
                  components={{
                    // Style links
                    a: ({ node, ...props }) => (
                      <a {...props} className="text-brand-600 hover:text-brand-700 underline" target="_blank" rel="noopener noreferrer" />
                    ),
                    // Style code blocks
                    code: ({ node, inline, ...props }: any) =>
                      inline ? (
                        <code {...props} className="rounded bg-slate-100 px-1.5 py-0.5 text-sm font-mono text-slate-900" />
                      ) : (
                        <code {...props} className="block rounded-md bg-slate-900 p-4 text-sm font-mono text-slate-100 overflow-x-auto" />
                      ),
                    // Style tables
                    table: ({ node, ...props }) => (
                      <div className="overflow-x-auto">
                        <table {...props} className="min-w-full divide-y divide-slate-200" />
                      </div>
                    ),
                    th: ({ node, ...props }) => (
                      <th {...props} className="bg-slate-50 px-4 py-2 text-left text-xs font-semibold text-slate-700" />
                    ),
                    td: ({ node, ...props }) => (
                      <td {...props} className="border-t border-slate-200 px-4 py-2 text-sm text-slate-900" />
                    ),
                  }}
                >
                  {content.content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

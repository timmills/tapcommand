export const NavTestPage = () => {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900">Testing Mode Active</h3>
            <p className="mt-1 text-sm text-blue-700">
              You're viewing the new hierarchical navigation. All pages under /nav-test use this new sidebar.
              <a href="/" className="ml-2 font-medium underline hover:text-blue-800">
                Return to original navigation
              </a>
            </p>
          </div>
        </div>
      </div>

      <header>
        <h2 className="text-lg font-semibold text-slate-900">Navigation UI Experiments</h2>
        <p className="text-sm text-slate-500">
          Testing hierarchical grouped navigation. Check out the new sidebar on the left!
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <h3 className="mb-3 text-md font-semibold text-slate-900">✨ What's New</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="text-brand-600">•</span>
              <span><strong>Collapsible groups</strong> - Click to expand/collapse sections</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brand-600">•</span>
              <span><strong>Icons</strong> - Visual anchors for each category</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brand-600">•</span>
              <span><strong>Nested items</strong> - Better organization of related pages</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brand-600">•</span>
              <span><strong>Role indicators</strong> - 🔒 shows restricted admin sections</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brand-600">•</span>
              <span><strong>Cmd+K hint</strong> - Ready for command palette integration</span>
            </li>
          </ul>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <h3 className="mb-3 text-md font-semibold text-slate-900">🎯 Benefits</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">✓</span>
              <span>Reduces visual clutter - hide what you don't need</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">✓</span>
              <span>Easier to find pages - logical grouping</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">✓</span>
              <span>Scalable - easy to add new features</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">✓</span>
              <span>Role-based access - hide entire groups by permission</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600">✓</span>
              <span>Modern design - follows 2024-2025 UI trends</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
        <h3 className="mb-2 text-md font-semibold text-amber-900">📝 Try It Out</h3>
        <p className="text-sm text-amber-800">
          Navigate to different pages using the new sidebar. The groups will stay open/closed as you navigate.
          Try collapsing the "Controllers" group, then clicking on "IR Libraries" - notice how smooth it feels?
        </p>
        <div className="mt-4 flex gap-2">
          <span className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-900 shadow-sm">
            Click group headers to toggle
          </span>
          <span className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-900 shadow-sm">
            Active page is highlighted
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h3 className="mb-3 text-md font-semibold text-slate-900">🔮 Future Enhancements</h3>
        <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2">
          <div>
            <strong className="text-slate-900">Command Palette (Cmd+K)</strong>
            <p className="text-xs text-slate-500 mt-1">Quick search and navigation like Linear/Vercel</p>
          </div>
          <div>
            <strong className="text-slate-900">Badge Notifications</strong>
            <p className="text-xs text-slate-500 mt-1">Show counts for offline devices, pending tasks</p>
          </div>
          <div>
            <strong className="text-slate-900">Favorites/Pinning</strong>
            <p className="text-xs text-slate-500 mt-1">Pin frequently used pages to top</p>
          </div>
          <div>
            <strong className="text-slate-900">Keyboard Shortcuts</strong>
            <p className="text-xs text-slate-500 mt-1">Navigate with arrow keys, numbers</p>
          </div>
        </div>
      </div>
    </div>
  );
};

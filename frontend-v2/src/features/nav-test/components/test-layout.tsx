import { HierarchicalNav } from './hierarchical-nav';

interface TestLayoutProps {
  children: React.ReactNode;
  title: string;
  description: string;
}

export const TestLayout = ({ children, title, description }: TestLayoutProps) => {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <HierarchicalNav />
      <main className="flex-1">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/70 backdrop-blur">
          <div className="mx-auto max-w-6xl px-4 py-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
              <p className="text-sm text-slate-500">{description}</p>
            </div>
          </div>
        </header>
        <div className="mx-auto max-w-6xl px-4 py-6">
          {children}
        </div>
      </main>
    </div>
  );
};

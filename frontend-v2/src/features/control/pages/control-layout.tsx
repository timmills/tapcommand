import { Outlet, useNavigate } from 'react-router-dom';

export const ControlLayout = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 text-slate-900">
      <header className="flex items-center justify-between px-6 py-4 shadow-sm shadow-slate-300/60 bg-white">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">SmartVenue Control</p>
          <h1 className="text-2xl font-semibold">Live IR Panel</h1>
        </div>
        <button
          type="button"
          onClick={() => navigate('/controllers')}
          className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:bg-slate-100"
        >
          Exit Control Mode
        </button>
      </header>
      <main className="flex-1 overflow-auto px-4 py-6">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

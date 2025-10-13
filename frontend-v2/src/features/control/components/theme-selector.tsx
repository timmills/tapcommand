import { useState } from 'react';

type Theme = {
  id: string;
  name: string;
  description: string;
  colors: {
    gradientFrom: string;
    gradientVia?: string;
    gradientTo: string;
    cardBg: string;
    cardBorder: string;
    cardBorderHover: string;
    primary: string;
    primaryHover: string;
    secondary: string;
    accent: string;
    textPrimary: string;
    textSecondary: string;
    success: string;
    danger: string;
    warning: string;
  };
};

const themes: Theme[] = [
  {
    id: 'neon-club',
    name: 'Neon Club',
    description: 'Vibrant pink and purple for high-energy venues',
    colors: {
      gradientFrom: '#667eea',
      gradientVia: '#764ba2',
      gradientTo: '#f093fb',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#FF006E',
      primary: '#FF006E',
      primaryHover: '#D4005E',
      secondary: '#8338EC',
      accent: '#00F5FF',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sports-bar',
    name: 'Sports Bar',
    description: 'Electric blue and orange for sports venues',
    colors: {
      gradientFrom: '#1e3a8a',
      gradientVia: '#3b82f6',
      gradientTo: '#60a5fa',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#00D9FF',
      primary: '#00D9FF',
      primaryHover: '#00B8D4',
      secondary: '#F97316',
      accent: '#10B981',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'premium-lounge',
    name: 'Premium Lounge',
    description: 'Sophisticated gold and deep slate',
    colors: {
      gradientFrom: '#0f172a',
      gradientVia: '#1e293b',
      gradientTo: '#334155',
      cardBg: 'rgba(255, 255, 255, 0.08)',
      cardBorder: 'rgba(255, 255, 255, 0.15)',
      cardBorderHover: '#FFD700',
      primary: '#FFD700',
      primaryHover: '#FFC700',
      secondary: '#06b6d4',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.6)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sunset-lounge',
    name: 'Sunset Lounge',
    description: 'Warm sunset colors for relaxed atmosphere',
    colors: {
      gradientFrom: '#ec4899',
      gradientVia: '#f97316',
      gradientTo: '#fbbf24',
      cardBg: 'rgba(255, 255, 255, 0.12)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#fbbf24',
      primary: '#fbbf24',
      primaryHover: '#f59e0b',
      secondary: '#ec4899',
      accent: '#f97316',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.8)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'ocean-breeze',
    name: 'Ocean Breeze',
    description: 'Cool teal and cyan for coastal venues',
    colors: {
      gradientFrom: '#0e7490',
      gradientVia: '#06b6d4',
      gradientTo: '#22d3ee',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#22d3ee',
      primary: '#22d3ee',
      primaryHover: '#06b6d4',
      secondary: '#3b82f6',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
];

interface ThemeSelectorProps {
  currentTheme: Theme;
  onThemeChange: (theme: Theme) => void;
}

export const ThemeSelector = ({ currentTheme, onThemeChange }: ThemeSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed left-6 top-6 z-30">
      {/* Theme Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-2xl backdrop-blur-xl transition-all hover:scale-105 active:scale-95"
        style={{
          backgroundColor: currentTheme.colors.cardBg,
          border: `2px solid ${currentTheme.colors.cardBorder}`,
          color: currentTheme.colors.textPrimary,
        }}
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
          />
        </svg>
        {currentTheme.name}
      </button>

      {/* Theme Picker Panel */}
      {isOpen && (
        <div
          className="mt-3 w-80 rounded-2xl p-4 shadow-2xl backdrop-blur-xl"
          style={{
            backgroundColor: currentTheme.colors.cardBg,
            border: `2px solid ${currentTheme.colors.cardBorder}`,
          }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h3
              className="text-lg font-bold"
              style={{ color: currentTheme.colors.textPrimary }}
            >
              Choose Theme
            </h3>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1 transition-all hover:bg-white/10"
              style={{ color: currentTheme.colors.textSecondary }}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-2">
            {themes.map((theme) => {
              const isActive = theme.id === currentTheme.id;
              return (
                <button
                  key={theme.id}
                  onClick={() => {
                    onThemeChange(theme);
                    setIsOpen(false);
                  }}
                  className="group w-full rounded-xl p-3 text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
                  style={{
                    background: `linear-gradient(135deg, ${theme.colors.gradientFrom}, ${theme.colors.gradientVia || theme.colors.gradientTo}, ${theme.colors.gradientTo})`,
                    border: isActive ? `3px solid ${theme.colors.primary}` : '2px solid rgba(255, 255, 255, 0.2)',
                    boxShadow: isActive ? `0 0 20px ${theme.colors.primary}50` : 'none',
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white">{theme.name}</div>
                      <div className="text-xs text-white/80">{theme.description}</div>
                    </div>
                    {isActive && (
                      <svg
                        className="h-6 w-6 text-white"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>

                  {/* Color Palette Preview */}
                  <div className="mt-2 flex gap-1">
                    {[theme.colors.primary, theme.colors.secondary, theme.colors.accent].map(
                      (color, i) => (
                        <div
                          key={i}
                          className="h-6 w-6 rounded-full border-2 border-white/50"
                          style={{ backgroundColor: color }}
                        />
                      )
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

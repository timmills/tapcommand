export type Theme = {
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

export const themes: Theme[] = [
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

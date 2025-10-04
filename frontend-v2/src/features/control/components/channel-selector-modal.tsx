import { useState, useMemo } from 'react';
import type { ChannelOption, ManagedDevice } from '@/types';

interface ChannelSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  channels: ChannelOption[];
  controllers: ManagedDevice[];
  selectedDeviceCount: number;
  onSelectChannel: (channelLcn: string) => void;
}

type ChannelCategory = 'in-use' | 'inhouse' | 'sports' | 'news' | 'fta' | 'entertainment' | 'kids' | 'all';

export const ChannelSelectorModal = ({
  isOpen,
  onClose,
  channels,
  controllers,
  selectedDeviceCount,
  onSelectChannel,
}: ChannelSelectorModalProps) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<ChannelCategory>('in-use');

  // Calculate channel usage from controllers
  const channelUsage = useMemo(() => {
    const usage = new Map<string, number>();
    controllers.forEach((controller) => {
      controller.ir_ports.forEach((port) => {
        if (port.default_channel) {
          usage.set(port.default_channel, (usage.get(port.default_channel) || 0) + 1);
        }
      });
    });
    return usage;
  }, [controllers]);

  // Categorize channels
  const categorizedChannels = useMemo(() => {
    const categories: Record<ChannelCategory, ChannelOption[]> = {
      'in-use': [],
      'inhouse': [],
      'sports': [],
      'news': [],
      'fta': [],
      'entertainment': [],
      'kids': [],
      'all': channels,
    };

    channels.forEach((channel) => {
      // In Use - channels that are set as defaults
      const lcn = channel.lcn?.split('/')[0].trim() || '';
      if (channelUsage.has(lcn)) {
        categories['in-use'].push(channel);
      }

      // InHouse
      if (channel.platform === 'InHouse') {
        categories['inhouse'].push(channel);
      }

      // FTA
      if (channel.platform === 'FTA') {
        categories['fta'].push(channel);
      }

      // Foxtel categorization by number range
      if (channel.foxtel_number) {
        const foxtelNum = parseInt(channel.foxtel_number, 10);
        if (foxtelNum >= 500 && foxtelNum < 600) {
          categories['sports'].push(channel);
        } else if (foxtelNum >= 600 && foxtelNum < 700) {
          // Sub-filter news channels
          if (
            channel.channel_name.toLowerCase().includes('news') ||
            channel.channel_name.toLowerCase().includes('cnn') ||
            channel.channel_name.toLowerCase().includes('bbc')
          ) {
            categories['news'].push(channel);
          } else {
            categories['entertainment'].push(channel);
          }
        } else if (foxtelNum >= 700 && foxtelNum < 800) {
          categories['kids'].push(channel);
        } else {
          categories['entertainment'].push(channel);
        }
      }
    });

    // Sort In Use by usage count
    categories['in-use'].sort((a, b) => {
      const aLcn = a.lcn?.split('/')[0].trim() || '';
      const bLcn = b.lcn?.split('/')[0].trim() || '';
      return (channelUsage.get(bLcn) || 0) - (channelUsage.get(aLcn) || 0);
    });

    return categories;
  }, [channels, channelUsage]);

  // Filter channels by search query
  const filteredChannels = useMemo(() => {
    const channelsToFilter = categorizedChannels[activeTab];
    if (!searchQuery.trim()) return channelsToFilter;

    const query = searchQuery.toLowerCase();
    return channelsToFilter.filter(
      (ch) =>
        ch.channel_name.toLowerCase().includes(query) ||
        ch.lcn?.toLowerCase().includes(query) ||
        ch.foxtel_number?.toLowerCase().includes(query) ||
        ch.broadcaster_network?.toLowerCase().includes(query)
    );
  }, [categorizedChannels, activeTab, searchQuery]);

  const handleSelectChannel = (channel: ChannelOption) => {
    const lcn = channel.lcn?.split('/')[0].trim() || channel.foxtel_number || '';
    onSelectChannel(lcn);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-xl font-semibold text-slate-900">
            Select Channel for {selectedDeviceCount} device{selectedDeviceCount === 1 ? '' : 's'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-slate-200 px-6 py-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search channels..."
            className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/20"
            autoFocus
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 overflow-x-auto border-b border-slate-200 px-6 py-3">
          {[
            { id: 'in-use', label: '⭐ In Use', count: categorizedChannels['in-use'].length },
            { id: 'inhouse', label: '🏢 InHouse', count: categorizedChannels['inhouse'].length },
            { id: 'sports', label: '🏆 Sports', count: categorizedChannels['sports'].length },
            { id: 'news', label: '📰 News', count: categorizedChannels['news'].length },
            { id: 'fta', label: '📺 FTA', count: categorizedChannels['fta'].length },
            { id: 'entertainment', label: '🎬 Entertainment', count: categorizedChannels['entertainment'].length },
            { id: 'kids', label: '👶 Kids', count: categorizedChannels['kids'].length },
            { id: 'all', label: '📡 All', count: categorizedChannels['all'].length },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as ChannelCategory)}
              className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition ${
                activeTab === tab.id
                  ? 'bg-brand-100 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>

        {/* Channel Grid */}
        <div className="max-h-96 overflow-y-auto p-6">
          {filteredChannels.length === 0 ? (
            <div className="py-12 text-center text-slate-500">
              {searchQuery ? 'No channels match your search' : 'No channels in this category'}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {filteredChannels.map((channel) => {
                const lcn = channel.lcn?.split('/')[0].trim() || '';
                const usageCount = channelUsage.get(lcn) || 0;

                return (
                  <button
                    key={channel.id}
                    type="button"
                    onClick={() => handleSelectChannel(channel)}
                    className="group relative rounded-xl border-2 border-slate-200 bg-white p-4 text-left transition hover:border-brand-400 hover:shadow-md"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h3 className="font-semibold text-slate-900 group-hover:text-brand-600">
                          {channel.channel_name}
                        </h3>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                          {channel.lcn && <span className="font-medium">LCN {channel.lcn}</span>}
                          {channel.foxtel_number && (
                            <span className="font-medium">Foxtel {channel.foxtel_number}</span>
                          )}
                        </div>
                        {channel.broadcaster_network && (
                          <p className="mt-1 text-xs text-slate-500">{channel.broadcaster_network}</p>
                        )}
                      </div>
                      {usageCount > 0 && (
                        <span className="rounded-full bg-brand-100 px-2 py-1 text-xs font-medium text-brand-700">
                          ✓ {usageCount}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
          <p className="text-sm text-slate-500">{filteredChannels.length} channels available</p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

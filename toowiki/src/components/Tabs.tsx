import type { Topic } from '../types';

interface TabsProps {
    topics: Topic[];
    activeId?: string | null;
    onSelect: (topicId: string) => void;
}

export default function Tabs({ topics, activeId, onSelect }: TabsProps) {
    if (topics.length === 0) {
        return <div className="px-7 text-slate-400 text-sm">No topics in this section yet.</div>;
    }

    return (
        <div className="flex flex-wrap gap-1 px-7 border-b border-slate-200 bg-white">
            {topics.map(topic => {
                const active = topic.id === activeId;
                const Icon = topic.icon;
                return (
                    <button
                        key={topic.id}
                        onClick={() => onSelect(topic.id)}
                        className={`px-5 py-2.5 text-sm flex items-center gap-2 whitespace-nowrap rounded-t-xl border-b-[3px] -mb-px transition ${
                            active
                                ? 'text-blue-600 font-semibold border-blue-600 bg-slate-50'
                                : 'text-slate-600 border-transparent hover:bg-slate-50'
                        }`}
                    >
                        <Icon className={`w-3.5 h-3.5 ${active ? 'text-blue-600' : 'text-slate-400'}`} />
                        {topic.name}
                    </button>
                );
            })}
        </div>
    );
}

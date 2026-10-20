import { FileText, Clock, Tag } from 'lucide-react';
import type { Category, SubCategory, Topic } from '../types';
import Tabs from './Tabs';
import KnowledgeCard from './KnowledgeCard';

interface MainAreaProps {
    category?: Category;
    sub?: SubCategory;
    topic?: Topic;
    onSelectTopic: (topicId: string) => void;
}

export default function MainArea({ category, sub, topic, onSelectTopic }: MainAreaProps) {
    if (!sub || !category) return null;

    return (
        <main className="flex-1 flex flex-col overflow-hidden">
            <div className="px-7 pt-5 pb-2 flex items-baseline gap-3">
                <h2 className="text-xl font-bold text-slate-900">{sub.name}</h2>
                <span className="text-sm text-slate-400">{category.name}</span>
            </div>

            <Tabs topics={sub.topics} activeId={topic?.id} onSelect={onSelectTopic} />

            <div className="flex-1 overflow-y-auto p-7">
                {topic ? (
                    <>
                        <div className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-4 mb-6">
                            {topic.cards.map(card => (
                                <KnowledgeCard key={card.id} card={card} />
                            ))}
                            {topic.cards.length === 0 && (
                                <span className="text-slate-400 text-sm">暂无卡片</span>
                            )}
                        </div>
                        <MetaRow meta={topic.meta} />
                    </>
                ) : (
                    <span className="text-slate-400 text-sm">暂无内容</span>
                )}
            </div>
        </main>
    );
}

function MetaRow({ meta = {} }: { meta?: Topic['meta'] }) {
    const items = [
        meta.articles !== undefined && { Icon: FileText, text: `${meta.articles} 篇文章` },
        meta.updated && { Icon: Clock, text: `最近更新: ${meta.updated}` },
        meta.topics !== undefined && { Icon: Tag, text: `${meta.topics} 个子主题` },
    ].filter(Boolean) as { Icon: typeof FileText; text: string }[];

    if (items.length === 0) return null;

    return (
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500 border-t border-slate-200 pt-3.5">
            {items.map((item, i) => (
                <span key={i} className="inline-flex items-center gap-1">
                    <item.Icon className="w-3 h-3 text-slate-400" />
                    {item.text}
                </span>
            ))}
        </div>
    );
}
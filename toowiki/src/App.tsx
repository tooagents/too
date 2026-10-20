import { useState, useMemo, useEffect } from 'react';
import type { Selection, KnowledgeData } from './types';
import { buildTree, type FlatNode } from './components/buildTree';
import Sidebar from './components/Sidebar';
import MainArea from './components/MainArea';
import { apiBaseUrl } from './config/app';

export default function App() {
    const [tree, setTree] = useState<KnowledgeData>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [navigationVersion, setNavigationVersion] = useState(0);
    const [selection, setSelection] = useState<Selection>({ category: '', sub: '', topic: null });

    useEffect(() => {
        fetch(`${apiBaseUrl}/wiki/tree`)
            .then(async response => {
                if (!response.ok) {
                    const payload = await response.json().catch(() => null) as { detail?: string } | null;
                    throw new Error(payload?.detail ?? `Request failed (HTTP ${response.status})`);
                }
                return response.json() as Promise<{ nodes: FlatNode[] }>;
            })
            .then(body => {
                const data = buildTree(body.nodes);
                setTree(data);
                const firstCategoryKey = Object.keys(data)[0];
                if (firstCategoryKey) {
                    const firstSub = data[firstCategoryKey].subcategories[0];
                    setSelection({
                        category: firstCategoryKey,
                        sub: firstSub?.id ?? '',
                        topic: firstSub?.topics[0]?.id ?? null,
                    });
                }
            })
            .catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to load the knowledge base.'))
            .finally(() => setLoading(false));
    }, []);

    const currentCategory = useMemo(() => tree[selection.category], [tree, selection.category]);
    const currentSub = useMemo(
        () => currentCategory?.subcategories.find(item => item.id === selection.sub),
        [currentCategory, selection.sub],
    );
    const currentTopic = useMemo(
        () => currentSub?.topics.find(item => item.id === selection.topic),
        [currentSub, selection.topic],
    );

    const handleSelectSub = (categoryKey: string, subId: string) => {
        const sub = tree[categoryKey]?.subcategories.find(item => item.id === subId);
        setSelection({ category: categoryKey, sub: subId, topic: sub?.topics[0]?.id ?? null });
        setNavigationVersion(version => version + 1);
    };

    const handleCardSaved = (cardId: string, title: string, content: string) => {
        setTree(previous => {
            const next = { ...previous };
            for (const [categoryKey, category] of Object.entries(previous)) {
                next[categoryKey] = {
                    ...category,
                    subcategories: category.subcategories.map(sub => ({
                        ...sub,
                        topics: sub.topics.map(topic => ({
                            ...topic,
                            cards: topic.cards.map(card => card.id === cardId
                                ? { ...card, title, desc: content }
                                : card),
                        })),
                    })),
                };
            }
            return next;
        });
    };

    if (loading) {
        return <div className="flex h-screen items-center justify-center text-sm text-slate-400">Loading knowledge base…</div>;
    }
    if (error) {
        return <div role="alert" className="flex h-screen items-center justify-center px-6 text-sm text-red-600">Unable to load the knowledge base: {error}</div>;
    }

    return (
        <div className="flex h-screen overflow-hidden bg-white">
            <Sidebar data={tree} selection={selection} onSelectSub={handleSelectSub} />
            <MainArea
                category={currentCategory}
                sub={currentSub}
                topic={currentTopic}
                navigationVersion={navigationVersion}
                onSelectTopic={topicId => setSelection(previous => ({ ...previous, topic: topicId }))}
                onCardSaved={handleCardSaved}
            />
        </div>
    );
}

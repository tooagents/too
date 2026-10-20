import { useEffect, useState } from 'react';
import { ArrowLeft, Clock, FileText, Pencil, Save, Tag, X } from 'lucide-react';
import type { Card, Category, SubCategory, Topic } from '../types';
import { apiBaseUrl } from '../config/app';
import Tabs from './Tabs';
import KnowledgeCard from './KnowledgeCard';

interface MainAreaProps {
    category?: Category;
    sub?: SubCategory;
    topic?: Topic;
    navigationVersion: number;
    onSelectTopic: (topicId: string) => void;
    onCardSaved: (cardId: string, title: string, content: string) => void;
}

export default function MainArea({ category, sub, topic, navigationVersion, onSelectTopic, onCardSaved }: MainAreaProps) {
    const [selectedCard, setSelectedCard] = useState<Card | null>(null);
    const [editing, setEditing] = useState(false);
    const [titleDraft, setTitleDraft] = useState('');
    const [contentDraft, setContentDraft] = useState('');
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);

    useEffect(() => {
        setSelectedCard(null);
        setEditing(false);
        setSaveError(null);
    }, [topic?.id, navigationVersion]);

    if (!sub || !category) return null;

    const openArticle = (card: Card) => {
        setSelectedCard(card);
        setTitleDraft(card.title);
        setContentDraft(card.desc);
        setSaveError(null);
    };

    const closeArticle = () => {
        setSelectedCard(null);
        setEditing(false);
        setSaveError(null);
    };

    const saveArticle = async () => {
        if (!selectedCard) return;
        setSaving(true);
        setSaveError(null);
        try {
            const response = await fetch(`${apiBaseUrl}/wiki/node/${selectedCard.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: titleDraft.trim(), content: contentDraft }),
            });
            const payload = await response.json().catch(() => null) as { detail?: string; node?: { name: string; content: string | null } } | null;
            if (!response.ok) throw new Error(payload?.detail ?? `Save failed (HTTP ${response.status})`);

            const savedTitle = payload?.node?.name ?? titleDraft.trim();
            const savedContent = payload?.node?.content ?? contentDraft;
            onCardSaved(selectedCard.id, savedTitle, savedContent);
            setSelectedCard({ ...selectedCard, title: savedTitle, desc: savedContent });
            setTitleDraft(savedTitle);
            setContentDraft(savedContent);
            setEditing(false);
        } catch (error) {
            setSaveError(error instanceof Error ? error.message : 'Unable to save this article.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <main className="flex-1 flex flex-col overflow-hidden bg-white">
            <div className="px-7 pt-5 pb-2 flex items-baseline gap-3">
                <h2 className="text-xl font-bold text-slate-900">{sub.name}</h2>
                <span className="text-sm text-slate-400">{category.name}</span>
            </div>

            <Tabs topics={sub.topics} activeId={topic?.id} onSelect={onSelectTopic} />

            <div className="flex-1 overflow-y-auto p-7">
                {selectedCard ? (
                    <article className="mx-auto max-w-3xl">
                        <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
                            <button type="button" onClick={closeArticle} className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900">
                                <ArrowLeft className="h-4 w-4" /> Back to articles
                            </button>
                            {editing ? (
                                <div className="flex items-center gap-2">
                                    <button type="button" onClick={() => { setEditing(false); setTitleDraft(selectedCard.title); setContentDraft(selectedCard.desc); setSaveError(null); }} disabled={saving} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                        <X className="h-4 w-4" /> Cancel
                                    </button>
                                    <button type="button" onClick={saveArticle} disabled={saving || !titleDraft.trim()} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                                        <Save className="h-4 w-4" /> {saving ? 'Saving…' : 'Save'}
                                    </button>
                                </div>
                            ) : (
                                <button type="button" onClick={() => setEditing(true)} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                                    <Pencil className="h-4 w-4" /> Edit
                                </button>
                            )}
                        </div>

                        {editing ? (
                            <div className="space-y-5">
                                <label className="block text-sm font-medium text-slate-700">
                                    Article title
                                    <input value={titleDraft} onChange={event => setTitleDraft(event.target.value)} maxLength={200} className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-2xl font-bold text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
                                </label>
                                <label className="block text-sm font-medium text-slate-700">
                                    Article content
                                    <textarea value={contentDraft} onChange={event => setContentDraft(event.target.value)} rows={18} className="mt-2 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 text-base leading-7 text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
                                </label>
                            </div>
                        ) : (
                            <>
                                <header className="border-b border-slate-200 pb-6">
                                    <div className="mb-4 flex items-center gap-2 text-sm text-blue-700">
                                        <span className="rounded-full bg-blue-50 px-3 py-1">{selectedCard.tag || 'Article'}</span>
                                    </div>
                                    <h1 className="text-4xl font-bold leading-tight tracking-tight text-slate-950">{selectedCard.title}</h1>
                                    <div className="mt-5 flex items-center gap-2 text-sm text-slate-400">
                                        <Clock className="h-4 w-4" /> Knowledge base article
                                    </div>
                                </header>
                                <div className="whitespace-pre-wrap py-8 text-base leading-8 text-slate-700">
                                    {selectedCard.desc || 'This article does not have any content yet.'}
                                </div>
                            </>
                        )}
                        {saveError && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{saveError}</p>}
                    </article>
                ) : topic ? (
                    <>
                        <div className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-4 mb-6">
                            {topic.cards.map(card => <KnowledgeCard key={card.id} card={card} onOpen={openArticle} />)}
                            {topic.cards.length === 0 && <span className="text-slate-400 text-sm">No articles yet.</span>}
                        </div>
                        <MetaRow meta={topic.meta} />
                    </>
                ) : (
                    <span className="text-slate-400 text-sm">No content available.</span>
                )}
            </div>
        </main>
    );
}

function MetaRow({ meta = {} }: { meta?: Topic['meta'] }) {
    const items = [
        meta.articles !== undefined && { Icon: FileText, text: `${meta.articles} articles` },
        meta.updated && { Icon: Clock, text: `Updated ${meta.updated}` },
        meta.topics !== undefined && { Icon: Tag, text: `${meta.topics} subtopics` },
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

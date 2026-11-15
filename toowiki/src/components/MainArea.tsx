import { Fragment, useEffect, useRef, useState } from 'react';
import { ArrowLeft, Bold, Clock, FileText, List, Pencil, Save, Tag, X } from 'lucide-react';
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
    const contentTextareaRef = useRef<HTMLTextAreaElement>(null);

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

    const applyBold = () => {
        const textarea = contentTextareaRef.current;
        if (!textarea) return;

        const { selectionStart, selectionEnd } = textarea;
        const selectedText = contentDraft.slice(selectionStart, selectionEnd);
        const replacement = selectedText ? `**${selectedText}**` : '**bold text**';
        setContentDraft(contentDraft.slice(0, selectionStart) + replacement + contentDraft.slice(selectionEnd));
        requestAnimationFrame(() => {
            textarea.focus();
            const selectionStartAfterFormat = selectionStart + 2;
            textarea.setSelectionRange(selectionStartAfterFormat, selectionStartAfterFormat + (selectedText || 'bold text').length);
        });
    };

    const applyList = () => {
        const textarea = contentTextareaRef.current;
        if (!textarea) return;

        const { selectionStart, selectionEnd } = textarea;
        const blockStart = contentDraft.lastIndexOf('\n', selectionStart - 1) + 1;
        const adjustedSelectionEnd = selectionEnd > selectionStart && contentDraft[selectionEnd - 1] === '\n'
            ? selectionEnd - 1
            : selectionEnd;
        const nextNewline = contentDraft.indexOf('\n', adjustedSelectionEnd);
        const blockEnd = nextNewline === -1 ? contentDraft.length : nextNewline;
        const lines = contentDraft.slice(blockStart, blockEnd).split('\n');
        const nonEmptyLines = lines.filter(line => line.trim());
        const isList = nonEmptyLines.length > 0 && nonEmptyLines.every(line => /^\s*[-*]\s+/.test(line));
        const replacement = lines.map(line => {
            if (!line.trim()) return line;
            return isList ? line.replace(/^(\s*)[-*]\s+/, '$1') : `- ${line}`;
        }).join('\n');

        setContentDraft(contentDraft.slice(0, blockStart) + replacement + contentDraft.slice(blockEnd));
        requestAnimationFrame(() => {
            textarea.focus();
            textarea.setSelectionRange(blockStart, blockStart + replacement.length);
        });
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
                                    <div className="mt-2 flex items-center gap-1 rounded-t-xl border border-slate-300 bg-slate-50 px-2 py-1">
                                        <button type="button" aria-label="Bold selected text" title="Bold" onMouseDown={event => event.preventDefault()} onClick={applyBold} className="rounded-md p-2 text-slate-600 hover:bg-slate-200 hover:text-slate-900">
                                            <Bold className="h-4 w-4" />
                                        </button>
                                        <button type="button" aria-label="Toggle bulleted list" title="Bulleted list" onMouseDown={event => event.preventDefault()} onClick={applyList} className="rounded-md p-2 text-slate-600 hover:bg-slate-200 hover:text-slate-900">
                                            <List className="h-4 w-4" />
                                        </button>
                                    </div>
                                    <textarea ref={contentTextareaRef} value={contentDraft} onChange={event => setContentDraft(event.target.value)} rows={18} className="w-full resize-y rounded-b-xl border border-t-0 border-slate-300 px-4 py-3 text-base font-normal leading-7 text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
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
                                    <ArticleContent content={selectedCard.desc || 'This article does not have any content yet.'} />
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

function ArticleContent({ content }: { content: string }) {
    const blocks: Array<{ type: 'text'; lines: string[] } | { type: 'list'; items: string[] }> = [];
    let textLines: string[] = [];
    let listItems: string[] = [];

    const flushText = () => {
        if (textLines.length) blocks.push({ type: 'text', lines: textLines });
        textLines = [];
    };
    const flushList = () => {
        if (listItems.length) blocks.push({ type: 'list', items: listItems });
        listItems = [];
    };

    for (const line of content.split('\n')) {
        const listItem = /^\s*[-*]\s+(.+)$/.exec(line);
        if (listItem) {
            flushText();
            listItems.push(listItem[1]);
        } else {
            flushList();
            textLines.push(line);
        }
    }
    flushText();
    flushList();

    return blocks.map((block, blockIndex) => block.type === 'list' ? (
        <ul key={blockIndex} className="my-3 list-disc pl-6">
            {block.items.map((item, itemIndex) => <li key={itemIndex}>{renderInlineMarkdown(item)}</li>)}
        </ul>
    ) : (
        <div key={blockIndex}>
            {block.lines.map((line, lineIndex) => (
                <Fragment key={lineIndex}>
                    {renderInlineMarkdown(line)}
                    {lineIndex < block.lines.length - 1 && <br />}
                </Fragment>
            ))}
        </div>
    ));
}

function renderInlineMarkdown(text: string) {
    return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => (
        part.startsWith('**') && part.endsWith('**')
            ? <strong key={index}>{part.slice(2, -2)}</strong>
            : part
    ));
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

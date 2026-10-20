import type { LucideIcon } from 'lucide-react';

export interface Card {
    id: string;
    icon: LucideIcon;
    title: string;
    desc: string;
    tag: string;
}

export interface TopicMeta {
    articles?: number;
    updated?: string;
    topics?: number;
}

export interface Topic {
    id: string;
    name: string;
    icon: LucideIcon;
    cards: Card[];
    meta?: TopicMeta;
}

export interface SubCategory {
    id: string;
    name: string;
    icon: LucideIcon;
    topics: Topic[];
}

export interface Category {
    name: string;
    icon: LucideIcon;
    subcategories: SubCategory[];
}

export type KnowledgeData = Record<string, Category>;

export interface Selection {
    category: string;
    sub: string;
    topic: string | null;
}
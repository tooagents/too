import * as Lucide from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { KnowledgeData, SubCategory, Topic, Card } from '../types';

/** Flat node returned by the API. */
export interface FlatNode {
    id: number;
    parent_id: number | null;
    level: number;
    name: string;
    icon: string | null;
    content: string | null;
    tag: string | null;
    sort_order: number;
}

const IconMap = Lucide as unknown as Record<string, LucideIcon>;

/** Map the stored icon name to a Lucide component, with FileQuestion as fallback. */
function toIcon(name: string | null): LucideIcon {
    return (name && IconMap[name]) || Lucide.FileQuestion;
}

export function buildTree(flat: FlatNode[]): KnowledgeData {
    // parent_id -> child nodes
    const childrenOf = new Map<number | null, FlatNode[]>();
    for (const n of flat) {
        const arr = childrenOf.get(n.parent_id) ?? [];
        arr.push(n);
        childrenOf.set(n.parent_id, arr);
    }
    // The API already sorts by level, sort_order, and id; keep the order stable here too.
    for (const arr of childrenOf.values()) {
        arr.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
    }

    const result: KnowledgeData = {};

    for (const cat of childrenOf.get(null) ?? []) {
        const subcategories: SubCategory[] = (childrenOf.get(cat.id) ?? []).map(sub => {
            const topics: Topic[] = (childrenOf.get(sub.id) ?? []).map(topic => {
                const cards: Card[] = (childrenOf.get(topic.id) ?? []).map(c => ({
                    id: String(c.id),
                    icon: toIcon(c.icon),
                    title: c.name,
                    desc: c.content ?? '',
                    tag: c.tag ?? '',
                }));
                return {
                    id: String(topic.id),
                    name: topic.name,
                    icon: toIcon(topic.icon),
                    cards,
                };
            });
            return {
                id: String(sub.id),
                name: sub.name,
                icon: toIcon(sub.icon),
                topics,
            };
        });
        result[String(cat.id)] = {
            name: cat.name,
            icon: toIcon(cat.icon),
            subcategories,
        };
    }

    return result;
}

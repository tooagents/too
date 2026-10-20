import { useState } from 'react';
import { ChevronRight, BookOpen } from 'lucide-react';
import type { KnowledgeData, Selection } from '../types';

interface SidebarProps {
    data: KnowledgeData;
    selection: Selection;
    onSelectSub: (categoryKey: string, subId: string) => void;
}

export default function Sidebar({ data, selection, onSelectSub }: SidebarProps) {
    const [expanded, setExpanded] = useState<Set<string>>(
        () => new Set([selection.category])
    );
    const [collapsed, setCollapsed] = useState(false); // 默认展开

    const toggle = (catKey: string) => {
        setExpanded(prev => {
            const next = new Set(prev);
            next.has(catKey) ? next.delete(catKey) : next.add(catKey);
            return next;
        });
    };

    return (
        <aside
            className={`shrink-0 bg-slate-50 border-r border-slate-200 flex flex-col overflow-y-auto p-3 transition-all duration-300 ${
                collapsed ? 'w-16' : 'w-72'
            }`}
        >
            {/* 头部：图标点击折叠/展开，图标本身不变 */}
            <div className={`flex items-center gap-2 px-3 pb-4 mb-4 border-b border-slate-200 ${collapsed ? 'justify-center' : ''}`}>
                <BookOpen
                    onClick={() => setCollapsed(!collapsed)}
                    className="w-7 h-7 text-blue-600 bg-white p-1.5 rounded-lg cursor-pointer shrink-0"
                />
                {!collapsed && (
                    <span className="font-bold text-lg text-slate-900 whitespace-nowrap">Knowledge Base</span>
                )}
            </div>

            {Object.entries(data).map(([catKey, cat]) => {
                const isOpen = expanded.has(catKey);
                const CatIcon = cat.icon;
                return (
                    <div key={catKey} className="mb-1">
                        <div
                            onClick={() => toggle(catKey)}
                            title={collapsed ? cat.name : undefined}
                            className={`flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer font-semibold text-sm text-slate-800 hover:bg-slate-200 select-none ${
                                collapsed ? 'justify-center' : ''
                            }`}
                        >
                            <CatIcon className="w-4 h-4 text-slate-500 shrink-0" />
                            {!collapsed && (
                                <>
                                    <span>{cat.name}</span>
                                    <ChevronRight
                                        className={`w-3.5 h-3.5 text-slate-400 ml-auto transition-transform ${isOpen ? 'rotate-90' : ''}`}
                                    />
                                </>
                            )}
                        </div>

                        {isOpen && !collapsed && (
                            <ul className="ml-5 pl-2 border-l-2 border-slate-300">
                                {cat.subcategories.map(sub => {
                                    const active = selection.sub === sub.id;
                                    const SubIcon = sub.icon;
                                    return (
                                        <li key={sub.id}>
                                            <a
                                                href="#"
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    onSelectSub(catKey, sub.id);
                                                }}
                                                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition ${
                                                    active
                                                        ? 'bg-blue-100 text-blue-800 font-semibold border-l-2 border-blue-600 -ml-0.5'
                                                        : 'text-slate-700 hover:bg-slate-200'
                                                }`}
                                            >
                                                <SubIcon className="w-3.5 h-3.5 text-slate-500" />
                                                {sub.name}
                                            </a>
                                        </li>
                                    );
                                })}
                            </ul>
                        )}
                    </div>
                );
            })}
        </aside>
    );
}
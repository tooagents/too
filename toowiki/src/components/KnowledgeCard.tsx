import type { Card } from '../types';

export default function KnowledgeCard({ card }: { card: Card }) {
    const Icon = card.icon;
    return (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col transition hover:border-slate-300 hover:bg-white hover:shadow-lg hover:-translate-y-0.5">
            <div className="flex items-center gap-2.5 mb-2.5">
                <Icon className="w-4 h-4 text-blue-600 bg-blue-50 p-1.5 box-content rounded-lg" />
                <h3 className="font-semibold text-sm text-slate-900">{card.title}</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed flex-1 mb-3.5">{card.desc}</p>
            <span className="text-[0.6rem] font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 uppercase self-start tracking-wide">
                {card.tag}
            </span>
        </div>
    );
}
import { useState, useMemo, useEffect } from 'react';
import type { Selection, KnowledgeData } from './types';
import { buildTree, type FlatNode } from './lib/buildTree';
import Sidebar from './components/Sidebar';
import MainArea from './components/MainArea';

export default function App() {
    // ⬇️ 唯一的结构改动：数据从 useState 空对象起步，useEffect 拉接口
    const [tree, setTree] = useState<KnowledgeData>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [selection, setSelection] = useState<Selection>({
        category: '',   // 初始为空，等数据到了再设
        sub: '',
        topic: null,
    });

    // ⬇️ 拉数据 + 组树 + 初始化 selection 到第一个大类/小类/小小类
    useEffect(() => {
        fetch('/api/wiki/tree', { credentials: 'include' })
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then((body: { nodes: FlatNode[] }) => {
                const data = buildTree(body.nodes);
                setTree(data);

                // 初始化选中第一个大类→小类→小小类
                const firstCatKey = Object.keys(data)[0];
                if (firstCatKey) {
                    const firstCat = data[firstCatKey];
                    const firstSub = firstCat.subcategories[0];
                    setSelection({
                        category: firstCatKey,
                        sub: firstSub?.id ?? '',
                        topic: firstSub?.topics[0]?.id ?? null,
                    });
                }
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    const currentCategory = useMemo(
        () => tree[selection.category],
        [tree, selection.category]
    );

    const currentSub = useMemo(
        () => currentCategory?.subcategories.find(s => s.id === selection.sub),
        [currentCategory, selection.sub]
    );

    const currentTopic = useMemo(
        () => currentSub?.topics.find(t => t.id === selection.topic),
        [currentSub, selection.topic]
    );

    const handleSelectSub = (categoryKey: string, subId: string) => {
        const sub = tree[categoryKey]?.subcategories.find(s => s.id === subId);
        setSelection({
            category: categoryKey,
            sub: subId,
            topic: sub?.topics[0]?.id ?? null,
        });
    };

    const handleSelectTopic = (topicId: string) => {
        setSelection(prev => ({ ...prev, topic: topicId }));
    };

    // ⬇️ 加载 / 错误态
    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center text-slate-400 text-sm">
                加载中…
            </div>
        );
    }
    if (error) {
        return (
            <div className="h-screen flex items-center justify-center text-red-500 text-sm">
                加载失败：{error}
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-white overflow-hidden">
            <Sidebar
                data={tree}
                selection={selection}
                onSelectSub={handleSelectSub}
            />
            <MainArea
                category={currentCategory}
                sub={currentSub}
                topic={currentTopic}
                onSelectTopic={handleSelectTopic}
            />
        </div>
    );
}

// import { useState, useMemo } from 'react';
// import type { Selection } from './types';
// import { knowledgeData } from './data';
// import Sidebar from './components/Sidebar';
// import MainArea from './components/MainArea';

// export default function App() {
//     const [selection, setSelection] = useState<Selection>({
//         category: 'cs',
//         sub: 'algorithms',
//         topic: 'sorting',
//     });

//     const currentCategory = useMemo(
//         () => knowledgeData[selection.category],
//         [selection.category]
//     );

//     const currentSub = useMemo(
//         () => currentCategory?.subcategories.find(s => s.id === selection.sub),
//         [currentCategory, selection.sub]
//     );

//     const currentTopic = useMemo(
//         () => currentSub?.topics.find(t => t.id === selection.topic),
//         [currentSub, selection.topic]
//     );

//     const handleSelectSub = (categoryKey: string, subId: string) => {
//         const sub = knowledgeData[categoryKey].subcategories.find(s => s.id === subId);
//         setSelection({
//             category: categoryKey,
//             sub: subId,
//             topic: sub?.topics[0]?.id ?? null,
//         });
//     };

//     const handleSelectTopic = (topicId: string) => {
//         setSelection(prev => ({ ...prev, topic: topicId }));
//     };

//     return (
//         <div className="flex h-screen bg-white overflow-hidden">
//             <Sidebar
//                 data={knowledgeData}
//                 selection={selection}
//                 onSelectSub={handleSelectSub}
//             />
//             <MainArea
//                 category={currentCategory}
//                 sub={currentSub}
//                 topic={currentTopic}
//                 onSelectTopic={handleSelectTopic}
//             />
//         </div>
//     );
// }
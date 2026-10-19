import { useState, useMemo } from 'react';
import { knowledgeData } from './data';
import Sidebar from './components/Sidebar';
import MainArea from './components/MainArea';

export default function App() {
    // 一个状态对象搞定三级选中
    const [selection, setSelection] = useState({
        category: 'cs',
        sub: 'algorithms',
        topic: 'sorting',
    });

    // 派生数据：当前分类/小类/小小类，都用 useMemo 避免重复查找
    const currentCategory = knowledgeData[selection.category];
    const currentSub = currentCategory.subcategories.find(s => s.id === selection.sub);
    const currentTopic = currentSub?.topics.find(t => t.id === selection.topic);

    // 选择小类时，自动把小小类重置到第一个
    const selectSub = (categoryKey, subId) => {
        const sub = knowledgeData[categoryKey].subcategories.find(s => s.id === subId);
        setSelection({
            category: categoryKey,
            sub: subId,
            topic: sub.topics[0]?.id ?? null,
        });
    };

    const selectTopic = (topicId) => {
        setSelection(prev => ({ ...prev, topic: topicId }));
    };

    return (
        <div className="flex h-screen bg-white overflow-hidden">
            <Sidebar
                data={knowledgeData}
                selection={selection}
                onSelectSub={selectSub}
            />
            <MainArea
                category={currentCategory}
                sub={currentSub}
                topic={currentTopic}
                onSelectTopic={selectTopic}
            />
        </div>
    );
}
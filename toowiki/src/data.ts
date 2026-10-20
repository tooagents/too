import {
    BookOpen, Laptop, Calculator, Globe, FlaskConical,
    // CS 小类
    GitBranch, Network, Database, Cpu,
    // CS 小小类
    ArrowDownWideNarrow, Route, Code2,
    // 排序卡片
    ArrowUp, Shuffle, Boxes, Layers,
    // 图算法
    Waypoints, Network as NetworkIcon, Search,
    // DP
    Package, AlignLeft, PencilLine, Coins,
    // 网络
    Layers as LayersIcon, ArrowLeftRight, Hand, Zap,
    // Web
    Wifi, Lock, Cookie, Gauge,
    // 数据库
    Table, Hash, Copy, Filter,
    // 事务
    Hourglass, Skull, RotateCcw,
    // OS
    ListChecks, ClipboardList, Handshake,
    // 内存
    MemoryStick, RefreshCw,
} from 'lucide-react';
import type { KnowledgeData } from './types';

export const knowledgeData: KnowledgeData = {
    cs: {
        name: '计算机科学',
        icon: Laptop,
        subcategories: [
            {
                id: 'algorithms',
                name: '算法与数据结构',
                icon: GitBranch,
                topics: [
                    {
                        id: 'sorting',
                        name: '排序算法',
                        icon: ArrowDownWideNarrow,
                        cards: [
                            { id: 'quicksort', icon: ArrowDownWideNarrow, title: '快速排序', desc: '分治思想，平均O(n log n)，原地排序但不稳定。基准选择影响性能。', tag: '排序' },
                            { id: 'mergesort', icon: Layers, title: '归并排序', desc: '稳定O(n log n)，需要额外空间。适合链表与大文件外部排序。', tag: '排序' },
                            { id: 'heapsort', icon: ArrowUp, title: '堆排序', desc: '利用二叉堆，原地O(n log n)。建堆O(n)，不稳定。', tag: '排序' },
                            { id: 'quickselect', icon: Shuffle, title: '快速选择', desc: 'Quickselect 平均O(n)找第k小元素。基于快排分区思想。', tag: '选择' },
                            { id: 'countingsort', icon: Boxes, title: '计数排序', desc: '非比较排序，O(n+k)。适合值域较小的整数。', tag: '线性' },
                        ],
                        meta: { articles: 18, updated: '2小时前', topics: 6 },
                    },
                    {
                        id: 'graph',
                        name: '图算法',
                        icon: Waypoints,
                        cards: [
                            { id: 'dijkstra', icon: Waypoints, title: 'Dijkstra算法', desc: '单源最短路径，非负权图。优先队列可达O((V+E)logV)。', tag: '最短路径' },
                            { id: 'bellmanford', icon: Route, title: 'Bellman-Ford', desc: '允许负权边，O(VE)。可检测负环。', tag: '最短路径' },
                            { id: 'mst', icon: GitBranch, title: '最小生成树', desc: 'Kruskal与Prim算法，用于网络设计。', tag: 'MST' },
                            { id: 'bfs', icon: Search, title: '广度优先搜索', desc: 'BFS，无权图最短路、层级遍历、连通分量。', tag: '遍历' },
                            { id: 'toposort', icon: Code2, title: '拓扑排序', desc: 'DAG线性排序，Kahn算法或DFS后序。任务调度基础。', tag: 'DAG' },
                        ],
                        meta: { articles: 12, updated: '昨天', topics: 4 },
                    },
                    {
                        id: 'dp',
                        name: '动态规划',
                        icon: Code2,
                        cards: [
                            { id: 'knapsack', icon: Package, title: '背包问题', desc: '0/1背包、完全背包。状态定义与转移方程是核心。', tag: '经典' },
                            { id: 'lcs', icon: AlignLeft, title: '最长公共子序列', desc: 'LCS，二维DP。用于diff工具、DNA比对。', tag: '序列' },
                            { id: 'editdistance', icon: PencilLine, title: '编辑距离', desc: 'Levenshtein距离，插入/删除/替换。拼写纠错与模糊匹配。', tag: '字符串' },
                            { id: 'coins', icon: Coins, title: '硬币找零', desc: '完全背包特例。最少硬币数与方案数两类变体。', tag: '经典' },
                        ],
                        meta: { articles: 9, updated: '3天前', topics: 3 },
                    },
                ],
            },
            {
                id: 'networking',
                name: '计算机网络',
                icon: Network,
                topics: [
                    {
                        id: 'protocols',
                        name: '网络协议',
                        icon: LayersIcon,
                        cards: [
                            { id: 'tcpip', icon: LayersIcon, title: 'TCP/IP 协议栈', desc: '四层模型：网络接口层、网际层、传输层、应用层。', tag: '协议' },
                            { id: 'handshake', icon: ArrowLeftRight, title: '三次握手', desc: 'SYN, SYN-ACK, ACK. 建立可靠连接。', tag: 'TCP' },
                            { id: 'wave', icon: Hand, title: '四次挥手', desc: 'FIN/ACK/ACK/FIN。TIME_WAIT 状态存在 2MSL。', tag: 'TCP' },
                            { id: 'udp', icon: Zap, title: 'UDP', desc: '无连接、不可靠、低开销。适合实时音视频、DNS。', tag: '传输层' },
                            { id: 'arp', icon: Route, title: 'ARP / ICMP', desc: '地址解析与差错控制。ping 基于 ICMP。', tag: '网际层' },
                        ],
                        meta: { articles: 15, updated: '昨天', topics: 5 },
                    },
                    {
                        id: 'http',
                        name: 'HTTP 与 Web',
                        icon: Globe,
                        cards: [
                            { id: 'http2', icon: Wifi, title: 'HTTP/2', desc: '多路复用、头部压缩、服务器推送。基于二进制分帧。', tag: '应用层' },
                            { id: 'tls', icon: Lock, title: 'HTTPS 与 TLS', desc: '证书链、握手过程、对称与非对称加密结合。', tag: '安全' },
                            { id: 'cookie', icon: Cookie, title: 'Cookie 与 Session', desc: '状态保持机制。Cookie 存客户端，Session 存服务端。', tag: '状态' },
                            { id: 'cdn', icon: Gauge, title: 'CDN 与缓存', desc: 'Cache-Control、ETag、CDN 边缘节点就近分发。', tag: '性能' },
                        ],
                        meta: { articles: 11, updated: '2天前', topics: 4 },
                    },
                ],
            },
            {
                id: 'databases',
                name: '数据库系统',
                icon: Database,
                topics: [
                    {
                        id: 'index',
                        name: '索引与存储',
                        icon: Table,
                        cards: [
                            { id: 'btree', icon: Table, title: 'B+树索引', desc: '多路平衡树，所有数据在叶子节点，范围查询高效。', tag: '索引' },
                            { id: 'hashindex', icon: Hash, title: '哈希索引', desc: 'O(1)等值查询，不支持范围。Memory引擎使用。', tag: '索引' },
                            { id: 'clustered', icon: Copy, title: '聚簇 vs 二级索引', desc: '聚簇索引决定物理顺序。二级索引需回表。', tag: 'InnoDB' },
                            { id: 'icp', icon: Filter, title: '索引下推', desc: 'ICP，减少回表次数。EXPLAIN 可观察。', tag: '优化' },
                        ],
                        meta: { articles: 10, updated: '3天前', topics: 3 },
                    },
                    {
                        id: 'transaction',
                        name: '事务与并发',
                        icon: Lock,
                        cards: [
                            { id: 'acid', icon: Lock, title: '事务ACID', desc: '原子性、一致性、隔离性、持久性。四种隔离级别。', tag: '事务' },
                            { id: 'mvcc', icon: Hourglass, title: 'MVCC', desc: '多版本并发控制，读写不阻塞。快照读与当前读。', tag: '并发' },
                            { id: 'phantom', icon: Skull, title: '幻读与间隙锁', desc: 'InnoDB 用 Next-Key Lock 解决幻读。', tag: '隔离' },
                            { id: 'wal', icon: RotateCcw, title: 'WAL 与 redo log', desc: '先写日志后写数据。崩溃恢复的基础。', tag: '持久化' },
                        ],
                        meta: { articles: 8, updated: '1周前', topics: 3 },
                    },
                ],
            },
            {
                id: 'os',
                name: '操作系统',
                icon: Cpu,
                topics: [
                    {
                        id: 'process',
                        name: '进程与线程',
                        icon: ListChecks,
                        cards: [
                            { id: 'procthread', icon: ListChecks, title: '进程 vs 线程', desc: '进程资源分配单位，线程调度单位。上下文切换开销不同。', tag: '基础' },
                            { id: 'scheduling', icon: ClipboardList, title: '调度算法', desc: 'FCFS、SJF、轮转、多级反馈队列。', tag: '调度' },
                            { id: 'mutex', icon: Lock, title: '互斥与信号量', desc: 'Mutex、Semaphore、条件变量。生产者-消费者模型。', tag: '同步' },
                            { id: 'deadlock', icon: Handshake, title: '死锁四条件', desc: '互斥、占有并等待、不可剥夺、循环等待。', tag: '并发' },
                        ],
                        meta: { articles: 9, updated: '5天前', topics: 3 },
                    },
                    {
                        id: 'memory',
                        name: '内存管理',
                        icon: MemoryStick,
                        cards: [
                            { id: 'virtual', icon: MemoryStick, title: '虚拟内存', desc: '页表、TLB、缺页中断。分页与分段。', tag: '内存' },
                            { id: 'replacement', icon: RefreshCw, title: '页面置换', desc: 'FIFO、LRU、Clock算法。抖动与工作集。', tag: '内存' },
                            { id: 'segpaging', icon: Layers, title: '段页式管理', desc: '先分段再分页，兼顾逻辑结构与物理管理。', tag: '内存' },
                        ],
                        meta: { articles: 7, updated: '1周前', topics: 2 },
                    },
                ],
            },
        ],
    },
    // ... 其余 math / humanities / science 同构补全，icon 换成 lucide 组件即可
};
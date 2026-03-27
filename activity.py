import sqlite3
import json
import datetime
import webbrowser
import os
import zlib
import tarfile
import tempfile
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

# ==========================================
# 1. 前端模板 (修复重叠粘连问题：引入 SizeCache 管理器)
# ==========================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>可话动态预览</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #f0f2f5; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        
        .moment-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            /* 重要：卡片本身必须是 block 且没有额外的 margin 干扰测量，间距由 padding-bottom 或外层容器控制 */
            box-sizing: border-box; 
        }
        
        @keyframes flash-bg { 0% { background-color: #e0f2fe; } 50% { background-color: #bae6fd; } 100% { background-color: transparent; } }
        .jump-highlight { animation: flash-bg 2s ease-out; }
    </style>
</head>
<body>
    <div id="root"></div>
    
    <script> 
        window.INJECTED_DATA = __JSON_DATA_PLACEHOLDER__; 
        window.TARGET_NAME = __TARGET_NAME_JSON__; 
    </script>
    
    <script type="text/babel">
        const { useState, useMemo, useRef, useEffect, memo, useCallback, useLayoutEffect } = React;
        
        const ClockIcon = memo(() => (<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>));

        const ESTIMATED_HEIGHT = 160; 
        const ITEM_SPACING = 20; // 卡片之间的间距

        // === 单条动态卡片组件 ===
        const ActivityCard = memo(({ item, isHighlighted, index, setSize }) => {
            const cardRef = useRef(null);

            useEffect(() => {
                if (!cardRef.current) return;
                
                // 使用 ResizeObserver 监听高度变化，这比 useLayoutEffect 更健壮
                const observer = new ResizeObserver(entries => {
                    for (let entry of entries) {
                        // 获取精确的高度（包含 padding 和 border）
                        const height = entry.borderBoxSize ? entry.borderBoxSize[0].blockSize : entry.target.getBoundingClientRect().height;
                        // 加上间距
                        setSize(index, height + ITEM_SPACING);
                    }
                });
                
                observer.observe(cardRef.current);
                return () => observer.disconnect();
            }, [index, setSize]);

            return (
                <div className="absolute w-full box-border px-4 transition-opacity duration-200" style={{ transform: `translateY(${item.offset}px)` }}>
                    <div ref={cardRef} className={`moment-card ${isHighlighted ? 'jump-highlight' : ''}`}>
                        <div className="flex items-start gap-3 mb-2">
                            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-lg shrink-0">
                                {window.TARGET_NAME[0]}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="font-bold text-[#2c3e50] text-lg truncate">{window.TARGET_NAME}</div>
                                <div className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                                    <ClockIcon /> {item.time}
                                </div>
                            </div>
                        </div>
                        <div className="text-[16px] text-[#1a1a1a] leading-relaxed whitespace-pre-wrap pl-[52px] break-words">
                            {item.content || <span className="text-gray-400 italic">(无文本内容)</span>}
                        </div>
                    </div>
                </div>
            );
        }); // 移除过多的 props 比较，让它自然刷新以避免位置更新滞后

        function App() {
            const [activities] = useState(window.INJECTED_DATA || []);
            const [searchTerm, setSearchTerm] = useState("");
            const [dateInput, setDateInput] = useState("");
            const [scrollTop, setScrollTop] = useState(0);
            const [highlightId, setHighlightId] = useState(null);
            
            // 使用 Map 来存储真实高度，避免 useState 异步带来的延迟
            const sizeMap = useRef({});
            // 强制刷新触发器
            const [, forceUpdate] = useState({});

            const scrollContainerRef = useRef(null);

            // 1. 过滤数据
            const filteredActivities = useMemo(() => {
                if (!searchTerm) return activities;
                const lower = searchTerm.toLowerCase();
                return activities.filter(a => a.content && String(a.content).toLowerCase().includes(lower));
            }, [activities, searchTerm]);

            // 当数据源变动时，清空高度缓存
            useEffect(() => {
                sizeMap.current = {};
                forceUpdate({});
            }, [filteredActivities]);

            // 2. 核心：动态偏移量计算器
            // 这是一个即时计算的过程，不依赖 state
            const getItemOffset = useCallback((index) => {
                let offset = 0;
                for (let i = 0; i < index; i++) {
                    const h = sizeMap.current[i] || ESTIMATED_HEIGHT;
                    offset += h;
                }
                return offset;
            }, []);

            const setSize = useCallback((index, size) => {
                // 只有当高度真正变化时才更新，避免死循环
                if (sizeMap.current[index] !== size) {
                    sizeMap.current[index] = size;
                    // 必须触发一次重绘，让所有后续的卡片重新计算 offset
                    // 使用 requestAnimationFrame 避免一帧内多次重绘
                    requestAnimationFrame(() => forceUpdate({}));
                }
            }, []);

            // 3. 计算可见区域
            // 这里我们不仅计算哪些可见，还顺便把每个 item 的 offset 算出来传递给子组件
            const { visibleItems, totalHeight } = useMemo(() => {
                const containerHeight = window.innerHeight;
                const items = [];
                let currentOffset = 0;
                
                // 先算出总高度，并找出可见项
                // 注意：这里为了消除“粘连”，我们每次 render 都必须重新根据 sizeMap 累加 offset
                // 虽然看起来是 O(N)，但在几千条数据的规模下 JS 运算极快，比 DOM 操作快得多
                
                // 优化：只计算到可见区域结束即可停止吗？不行，因为滚动条需要 totalHeight
                // 这里的性能瓶颈在于循环。对于 10000 条以下数据，for 循环没问题。
                
                let startIndex = -1;
                let endIndex = -1;
                const buffer = 600; // 像素缓冲

                for (let i = 0; i < filteredActivities.length; i++) {
                    const h = sizeMap.current[i] || ESTIMATED_HEIGHT;
                    const nextOffset = currentOffset + h;

                    // 判断可见性
                    if (nextOffset >= scrollTop - buffer && currentOffset <= scrollTop + containerHeight + buffer) {
                        items.push({
                            ...filteredActivities[i],
                            index: i,
                            offset: currentOffset // 将计算好的 offset 直接传给子组件
                        });
                    }
                    currentOffset = nextOffset;
                }

                return { visibleItems: items, totalHeight: currentOffset };
            }, [scrollTop, filteredActivities, sizeMap.current]); // 依赖 sizeMap.current 的变更触发的重绘

            // 4. 滚动监听
            const onScroll = useCallback((e) => {
                setScrollTop(e.target.scrollTop);
            }, []);

            // 5. 跳转逻辑
            const jumpToDate = (targetDate) => {
                setDateInput(targetDate);
                if (!targetDate) return;
                
                const targetIndex = filteredActivities.findIndex(a => {
                    const aDate = a.time.substring(0, 10); 
                    return aDate <= targetDate; 
                });
                
                if (targetIndex !== -1) {
                    // 重新即时计算 offset
                    let targetTop = 0;
                    for(let i=0; i<targetIndex; i++) targetTop += (sizeMap.current[i] || ESTIMATED_HEIGHT);
                    
                    if (scrollContainerRef.current) {
                        scrollContainerRef.current.scrollTo({ top: targetTop, behavior: 'auto' });
                    }
                    setHighlightId(filteredActivities[targetIndex].id);
                } else {
                     if (filteredActivities.length > 0) {
                        alert("该日期过早，为您跳转到最早的一条记录");
                        const lastIndex = filteredActivities.length - 1;
                         // 重新即时计算 offset
                        let targetTop = 0;
                        for(let i=0; i<lastIndex; i++) targetTop += (sizeMap.current[i] || ESTIMATED_HEIGHT);

                        scrollContainerRef.current.scrollTo({ top: targetTop, behavior: 'auto' });
                        setHighlightId(filteredActivities[lastIndex].id);
                    } else {
                        alert("没有相关动态");
                    }
                }
            };
            
            useEffect(() => { if (window.lucide) window.lucide.createIcons(); }, []);

            return (
                <div className="flex w-screen h-screen bg-[#f0f2f5]">
                    {/* 侧边栏 */}
                    <div className="w-80 bg-white border-r border-gray-200 flex flex-col flex-shrink-0 z-20 shadow-sm">
                        <div className="h-16 flex items-center px-6 border-b border-gray-100">
                            <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                                <i data-lucide="feather" className="text-orange-500"></i>动态胶囊
                            </h1>
                        </div>
                        <div className="p-4 space-y-4 flex-1 overflow-y-auto">
                            <div className="relative">
                                <i data-lucide="search" className="absolute left-3 top-2.5 w-4 h-4 text-gray-400"></i>
                                <input type="text" 
                                    className="w-full bg-gray-50 border border-gray-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-2 focus:ring-orange-500 outline-none" 
                                    placeholder="搜索动态内容..." 
                                    value={searchTerm} 
                                    onChange={(e) => { setSearchTerm(e.target.value); if(scrollContainerRef.current) scrollContainerRef.current.scrollTop = 0; }} 
                                />
                            </div>
                            <div className="space-y-1 mt-4">
                                <label className="text-xs font-semibold text-gray-400 uppercase">跳转至日期</label>
                                <input type="date" className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm" 
                                    value={dateInput} 
                                    onChange={(e) => jumpToDate(e.target.value)} 
                                />
                            </div>
                             <div className="bg-orange-50 rounded-xl p-4 border border-orange-100 mt-4">
                                <div className="text-xs font-semibold text-orange-400 mb-2 uppercase">统计</div>
                                <div className="text-sm"><span className="text-gray-600">总数：</span><span className="font-bold">{filteredActivities.length}</span></div>
                                <div className="text-sm mt-1"><span className="text-gray-600">用户：</span><span className="font-bold text-orange-600 truncate">{window.TARGET_NAME}</span></div>
                            </div>
                        </div>
                    </div>

                    {/* 主内容区 */}
                    <div className="flex-1 flex flex-col h-full relative min-w-0">
                         <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 shrink-0 z-10 shadow-sm">
                            <div className="font-bold text-gray-700 text-lg">
                                {activities.length > 0 ? `${window.TARGET_NAME} 的动态` : ""}
                            </div>
                         </div>
                         
                        <div 
                            className="flex-1 overflow-y-auto relative will-change-scroll" 
                            ref={scrollContainerRef} 
                            onScroll={onScroll}
                        >
                            <div style={{ height: totalHeight, width: '100%', maxWidth: '800px', margin: '0 auto', position: 'relative' }}>
                                {visibleItems.map((item) => (
                                    <ActivityCard 
                                        key={item.id} 
                                        index={item.index}
                                        item={item} 
                                        isHighlighted={item.id === highlightId}
                                        setSize={setSize}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            );
        }
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

# ==========================================
# 2. 后端核心逻辑 (完全保持不变)
# ==========================================

def extract_and_parse_backup(file_path):
    temp_dir = tempfile.mkdtemp()
    db_path = None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.db': 
            db_name = os.path.basename(file_path)
            dest_path = os.path.join(temp_dir, db_name)
            shutil.copy2(file_path, dest_path)
            return dest_path, temp_dir
        
        with open(file_path, 'rb') as f: raw_data = f.read()
        marker = b'ANDROID BACKUP'
        start_index = raw_data.find(marker)
        ab_data = raw_data[start_index:] if start_index != -1 else raw_data
        header_end_pos = 0
        newline_count = 0
        for i in range(min(1000, len(ab_data))):
            if ab_data[i] == 10: 
                newline_count += 1
                if newline_count == 4: header_end_pos = i + 1; break
        
        header_lines = ab_data[:header_end_pos].split(b'\n')
        is_compressed = True
        if len(header_lines) > 2: is_compressed = (header_lines[2].strip() == b'1')
        body_data = ab_data[header_end_pos:]
        try: tar_stream = zlib.decompress(body_data) if is_compressed else body_data
        except: tar_stream = body_data
        
        tar_path = os.path.join(temp_dir, 'backup.tar')
        with open(tar_path, 'wb') as f: f.write(tar_stream)
        
        target_suffix = 'apps/com.app.tideswing/db/TideSwing.db'
        found = False
        with tarfile.open(tar_path, 'r') as tar:
            target_member = None
            try: target_member = tar.getmember(target_suffix)
            except KeyError:
                for member in tar.getmembers():
                    if member.name.endswith('TideSwing.db'): target_member = member; break
            if target_member:
                tar.extract(target_member, path=temp_dir)
                db_path = os.path.join(temp_dir, target_member.name)
                found = True
        if not found: raise Exception("未找到数据库文件")
        return db_path, temp_dir
    except Exception as e:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        raise e

def get_activity_users_from_db(db_path):
    users = {} 
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t_reference_activity'")
        if not cursor.fetchone(): conn.close(); return []
        cursor.execute("PRAGMA table_info(t_reference_activity)")
        columns = [col[1] for col in cursor.fetchall()]
        nick_col = 'NICKNAME' if 'NICKNAME' in columns else ('nickname' if 'nickname' in columns else None)
        id_col = None
        for k in ['USER_ID', 'user_id', 'uid', 'UID']:
            if k in columns: id_col = k; break
        if not nick_col: conn.close(); return []
        query = f"SELECT DISTINCT {nick_col} {', ' + id_col if id_col else ''} FROM t_reference_activity"
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            name = row[nick_col]
            if not name: continue
            uid = row[id_col] if id_col else f"name_{name}"
            users[name] = {"id": str(uid), "name": name, "key_val": name} 
        conn.close()
        return list(users.values())
    except Exception as e:
        print(f"Error reading users: {e}")
        return []

def query_activities_from_db(db_path, target_name):
    activities = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(t_reference_activity)")
        columns = [col[1] for col in cursor.fetchall()]
        content_col = 'ACTIVITIES_TEXT' if 'ACTIVITIES_TEXT' in columns else 'activities_text'
        nick_col = 'NICKNAME' if 'NICKNAME' in columns else 'nickname'
        time_col = None
        for k in ['CREATE_TIME', 'create_time', 'time', 'TIME', 'timestamp']:
            if k in columns: time_col = k; break
        id_col = None
        for k in ['ID', 'id', '_id']:
            if k in columns: id_col = k; break
        if not content_col or not nick_col or not time_col: conn.close(); return []
        query = f"SELECT * FROM t_reference_activity WHERE {nick_col} = ?"
        cursor.execute(query, (target_name,))
        rows = cursor.fetchall()
        for row in rows:
            raw_id = row[id_col] if id_col else f"{row[time_col]}"
            content = row[content_col]
            raw_time_val = row[time_col]
            full_time = "Unknown"
            ts = 0
            if raw_time_val:
                try:
                    time_str = str(raw_time_val).strip()
                    try:
                        dt = datetime.datetime.strptime(time_str, '%y-%m-%d %H-%M')
                        full_time = dt.strftime('%Y-%m-%d %H:%M')
                        ts = dt.timestamp()
                    except ValueError:
                        try:
                            dt = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                            full_time = time_str
                            ts = dt.timestamp()
                        except ValueError:
                            ts_float = float(time_str)
                            if ts_float > 10000000000: ts_float /= 1000.0
                            dt = datetime.datetime.fromtimestamp(ts_float)
                            full_time = dt.strftime('%Y-%m-%d %H:%M')
                            ts = ts_float
                except:
                    full_time = str(raw_time_val)
                    ts = 0
            activities.append({
                "id": str(raw_id),
                "timestamp": ts, 
                "content": content,
                "time": full_time 
            })
        conn.close()
        return activities
    except Exception as e:
        print(f"Error querying activities: {e}")
        return []

# ==========================================
# 3. GUI 主程序
# ==========================================

class ActivityAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("可话动态提取器 - Activity Viewer")
        self.root.geometry("600x750")
        
        self.data_sources = [] 
        self.temp_dirs = []     
        self.users = []      
        self.current_display_users = [] 
        
        style = ttk.Style()
        style.configure("TButton", padding=5)
        
        frame_header = ttk.Frame(root)
        frame_header.pack(fill="x", padx=10, pady=10)
        lbl_title = ttk.Label(frame_header, text="✨ 支持作者 & 源码下载", font=("Arial", 10, "bold"), foreground="#FF9800")
        lbl_title.pack(side="top", pady=(0, 5))
        link_frame = ttk.Frame(frame_header)
        link_frame.pack(side="top")
        lbl_github = tk.Label(link_frame, text="[GitHub]", font=("Arial", 9, "underline"), fg="blue", cursor="hand2")
        lbl_github.pack(side="left", padx=10)
        lbl_github.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/alicebob142857/kehua-chat-record-export"))
        lbl_gitee = tk.Label(link_frame, text="[Gitee]", font=("Arial", 9, "underline"), fg="red", cursor="hand2")
        lbl_gitee.pack(side="left", padx=10)
        lbl_gitee.bind("<Button-1>", lambda e: webbrowser.open("https://gitee.com/alicebob142857/kehua"))

        frame_top = ttk.LabelFrame(root, text="第一步：导入文件 (.ab / .bak / .db / .json)", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        self.file_listbox = tk.Listbox(frame_top, height=4, font=("Arial", 9), fg="#555")
        self.file_listbox.pack(side="left", fill="both", expand=True, padx=(0,5))
        btn_frame = ttk.Frame(frame_top)
        btn_frame.pack(side="right", fill="y")
        ttk.Button(btn_frame, text="➕ 添加文件", command=self.add_files).pack(fill="x", pady=(0,5))
        ttk.Button(btn_frame, text="🗑️ 清空列表", command=self.clear_files).pack(fill="x", pady=(0,5))
        self.btn_analyze = ttk.Button(btn_frame, text="🚀 解析动态", command=self.do_analyze_process, state="disabled")
        self.btn_analyze.pack(fill="x", side="bottom")

        frame_mid = ttk.LabelFrame(root, text="第二步：选择发布人 (查看该用户动态)", padding=10)
        frame_mid.pack(fill="both", expand=True, padx=10, pady=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_users)
        search_frame = ttk.Frame(frame_mid)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="🔍 搜索昵称:", font=("Arial", 9)).pack(side="left")
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, state="disabled")
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(5,0))
        list_frame = ttk.Frame(frame_mid)
        list_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.user_listbox = tk.Listbox(list_frame, height=10, selectmode="single", exportselection=False, yscrollcommand=scrollbar.set, font=("Arial", 10))
        self.user_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.user_listbox.yview)
        self.user_listbox.bind("<<ListboxSelect>>", self.on_select_change)

        frame_action = ttk.Frame(root)
        frame_action.pack(pady=10, fill="x", padx=20)
        btn_box = ttk.Frame(frame_action)
        btn_box.pack(fill="x")
        self.btn_preview = ttk.Button(btn_box, text="👀 立即查看", command=self.do_preview, state="disabled")
        self.btn_preview.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=5)
        self.btn_export_json = ttk.Button(btn_box, text="📄 导出 JSON", command=self.do_export_json, state="disabled")
        self.btn_export_json.pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=5)
        self.progress = ttk.Progressbar(root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(10, 0))
        self.lbl_status = ttk.Label(root, text="请先添加备份文件", foreground="gray")
        self.lbl_status.pack(side="bottom", pady=10)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Backup/JSON", "*.bak *.ab *.db *.json")])
        if not files: return
        for f in files:
            if f not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, f)
        if self.file_listbox.size() > 0:
            self.btn_analyze.config(state="normal")
            self.lbl_status.config(text=f"已准备 {self.file_listbox.size()} 个文件", foreground="blue")

    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.btn_analyze.config(state="disabled")
        self.cleanup_temps()
        self.data_sources = []
        self.users = []
        self.update_user_listbox([])
        self.lbl_status.config(text="列表已清空")
        self.progress['value'] = 0

    def do_analyze_process(self):
        raw_files = self.file_listbox.get(0, tk.END)
        if not raw_files: return
        self.lbl_status.config(text="正在解析动态数据...", foreground="orange")
        self.progress['value'] = 0
        self.progress['maximum'] = len(raw_files)
        self.root.update()
        self.cleanup_temps()
        self.data_sources = []
        valid_count = 0
        merged_users_dict = {}

        for i, f_path in enumerate(raw_files):
            try:
                ext = os.path.splitext(f_path)[1].lower()
                if ext == '.json':
                    with open(f_path, 'r', encoding='utf-8') as jf:
                        j_data = json.load(jf)
                        if isinstance(j_data, dict) and 'meta' in j_data:
                            name = j_data['meta'].get('name', 'Unknown')
                            merged_users_dict[name] = {'name': name, 'key_val': name}
                            self.data_sources.append({'type': 'json', 'data': j_data})
                            valid_count += 1
                else:
                    db_path, temp_dir = extract_and_parse_backup(f_path)
                    self.temp_dirs.append(temp_dir)
                    self.data_sources.append({'type': 'db', 'path': db_path})
                    users = get_activity_users_from_db(db_path)
                    for u in users: merged_users_dict[u['name']] = u
                    valid_count += 1
            except Exception as e:
                print(f"File Error: {f_path} -> {e}")
            self.progress['value'] = i + 1
            self.root.update()
        
        self.users = list(merged_users_dict.values())
        if valid_count == 0:
            messagebox.showerror("错误", "所有文件均解析失败")
            return
        self.update_user_listbox(self.users)
        self.entry_search.config(state="normal")
        self.lbl_status.config(text=f"加载完成，找到 {len(self.users)} 位发布动态的用户", foreground="green")

    def update_user_listbox(self, user_list):
        self.user_listbox.delete(0, tk.END)
        self.current_display_users = user_list
        for u in user_list: self.user_listbox.insert(tk.END, u['name'])

    def filter_users(self, *args):
        keyword = self.search_var.get().lower()
        if not keyword: self.update_user_listbox(self.users); return
        filtered = [u for u in self.users if keyword in u['name'].lower()]
        self.update_user_listbox(filtered)

    def on_select_change(self, event):
        if self.user_listbox.curselection():
            self.btn_preview.config(state="normal")
            self.btn_export_json.config(state="normal")
        else:
            self.btn_preview.config(state="disabled")
            self.btn_export_json.config(state="disabled")

    def get_merged_activities(self, target_name):
        all_activities = []
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.data_sources) + 1
        for i, src in enumerate(self.data_sources):
            if src['type'] == 'db':
                acts = query_activities_from_db(src['path'], target_name)
                all_activities.extend(acts)
            elif src['type'] == 'json':
                meta = src['data'].get('meta', {})
                if meta.get('name') == target_name:
                    all_activities.extend(src['data'].get('activities', []))
            self.progress['value'] = i + 1
            self.root.update()
        
        unique_acts = []
        seen = set()
        # 核心：必须按时间倒序排列 (最新的在最前面)
        all_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        for act in all_activities:
            fingerprint = f"{act['time']}_{act['content']}"
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_acts.append(act)
        self.progress['value'] = self.progress['maximum']
        return unique_acts

    def do_preview(self):
        sel = self.user_listbox.curselection()
        if not sel: return
        user = self.current_display_users[sel[0]]
        self.lbl_status.config(text="正在生成预览...", foreground="blue")
        try:
            activities = self.get_merged_activities(user['name'])
            if not activities:
                messagebox.showinfo("提示", "该用户没有动态记录")
                return
            json_str = json.dumps(activities, ensure_ascii=False)
            name_json = json.dumps(user['name'], ensure_ascii=False)
            html = HTML_TEMPLATE.replace("__JSON_DATA_PLACEHOLDER__", json_str)
            html = html.replace("__TARGET_NAME_JSON__", name_json)
            temp_path = os.path.join(tempfile.gettempdir(), "kehua_moments_preview.html")
            with open(temp_path, 'w', encoding='utf-8') as f: f.write(html)
            webbrowser.open('file://' + temp_path)
            self.lbl_status.config(text=f"预览已打开 ({len(activities)} 条动态)", foreground="green")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def do_export_json(self):
        sel = self.user_listbox.curselection()
        if not sel: return
        user = self.current_display_users[sel[0]]
        default_name = f"{user['name']}的动态.json"
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile=default_name, title="导出 JSON")
        if not save_path: return
        self.lbl_status.config(text="正在导出 JSON...", foreground="blue")
        try:
            activities = self.get_merged_activities(user['name'])
            if not activities: messagebox.showinfo("提示", "该用户没有动态记录"); return
            simple_data = []
            for act in activities: simple_data.append({"content": act['content'], "time": act['time']})
            final_json = {"meta": {"name": user['name'], "type": "activity_export_simple"}, "activities": simple_data}
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, ensure_ascii=False, indent=2)
            self.lbl_status.config(text=f"导出成功 ({len(simple_data)} 条)", foreground="green")
            messagebox.showinfo("成功", f"已导出至: {save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def cleanup_temps(self):
        for d in self.temp_dirs:
            if os.path.exists(d):
                try: shutil.rmtree(d)
                except: pass
        self.temp_dirs = []

    def __del__(self):
        self.cleanup_temps()

if __name__ == "__main__":
    root = tk.Tk()
    app = ActivityAppGUI(root)
    root.mainloop()
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

# ==========================================
# 1. 前端模板 (保持不变)
# ==========================================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>可话记忆胶囊</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #f5f5f5; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        .bubble-left::before { content: ""; position: absolute; left: -10px; top: 10px; border-top: 6px solid transparent; border-bottom: 6px solid transparent; border-right: 10px solid white; }
        .bubble-right::before { content: ""; position: absolute; right: -10px; top: 10px; border-top: 6px solid transparent; border-bottom: 6px solid transparent; border-left: 10px solid #95ec69; }
        .recalled-bubble { opacity: 0.7; }
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
        const { useState, useMemo, useRef, useEffect } = React;
        const UserIcon = () => (<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>);
        const LocateIcon = () => (<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>);
        const ITEM_HEIGHT = 80; const BUFFER_SIZE = 20;

        function App() {
            const [messages, setMessages] = useState(window.INJECTED_DATA || []);
            const [searchTerm, setSearchTerm] = useState("");
            const [dateInput, setDateInput] = useState("");
            const [scrollTop, setScrollTop] = useState(0);
            const [highlightId, setHighlightId] = useState(null);
            const scrollContainerRef = useRef(null);

            if (!messages || messages.length === 0) return <div className="h-screen flex items-center justify-center text-gray-500">暂无数据</div>;

            const filteredMessages = useMemo(() => {
                if (!searchTerm) return messages;
                return messages.filter(msg => msg.content && String(msg.content).toLowerCase().includes(searchTerm.toLowerCase()));
            }, [messages, searchTerm]);

            const jumpToMessageContext = (originalIndex, msgId) => {
                setSearchTerm("");
                const targetScrollTop = originalIndex * ITEM_HEIGHT;
                setTimeout(() => {
                    if (scrollContainerRef.current) scrollContainerRef.current.scrollTop = targetScrollTop;
                    setHighlightId(msgId || originalIndex);
                }, 10);
            };

            const jumpToDate = (targetDate) => {
                setDateInput(targetDate);
                if (!targetDate) return;
                setSearchTerm("");
                setTimeout(() => {
                    const targetIndex = messages.findIndex(m => m.date >= targetDate);
                    if (targetIndex !== -1) {
                        const targetScrollTop = targetIndex * ITEM_HEIGHT;
                        if (scrollContainerRef.current) scrollContainerRef.current.scrollTop = targetScrollTop;
                        setHighlightId(messages[targetIndex].id || targetIndex);
                    } else { alert("该日期之后没有相关记录"); }
                }, 10);
            };

            const totalHeight = filteredMessages.length * ITEM_HEIGHT;
            const { startIndex, endIndex, visibleData, offsetY } = useMemo(() => {
                const containerHeight = window.innerHeight;
                let start = Math.floor(scrollTop / ITEM_HEIGHT) - BUFFER_SIZE; start = Math.max(0, start);
                let end = Math.floor((scrollTop + containerHeight) / ITEM_HEIGHT) + BUFFER_SIZE; end = Math.min(filteredMessages.length, end);
                return { startIndex: start, endIndex: end, visibleData: filteredMessages.slice(start, end), offsetY: start * ITEM_HEIGHT };
            }, [scrollTop, filteredMessages]);

            const onScroll = (e) => { requestAnimationFrame(() => setScrollTop(e.target.scrollTop)); };
            useEffect(() => { if (searchTerm && scrollContainerRef.current) scrollContainerRef.current.scrollTop = 0; }, [searchTerm]);
            useEffect(() => { if (window.lucide) window.lucide.createIcons(); }, []);

            return (
                <div className="flex w-screen h-screen bg-[#f5f5f5]">
                    <div className="w-80 bg-white border-r border-gray-200 flex flex-col flex-shrink-0 z-20 shadow-sm">
                        <div className="h-16 flex items-center px-6 border-b border-gray-100"><h1 className="text-xl font-bold text-gray-800 flex items-center gap-2"><i data-lucide="message-circle" className="text-blue-500"></i>时光胶囊</h1></div>
                        <div className="p-4 space-y-4 flex-1 overflow-y-auto">
                            <div className="relative"><i data-lucide="search" className="absolute left-3 top-2.5 w-4 h-4 text-gray-400"></i><input type="text" className="w-full bg-gray-50 border border-gray-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none" placeholder="搜索内容..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div>
                            <div className="space-y-1 mt-4"><label className="text-xs font-semibold text-gray-400 uppercase">跳转至日期</label><input type="date" min="2020-01-01" className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm" value={dateInput} onChange={(e) => jumpToDate(e.target.value)} /></div>
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 mt-4"><div className="text-xs font-semibold text-gray-400 mb-2 uppercase">统计</div><div className="flex justify-between items-center text-sm"><span className="text-gray-600">总条数</span><span className="font-bold text-gray-800">{filteredMessages.length}</span></div><div className="flex justify-between items-center text-sm mt-1"><span className="text-gray-600">对象</span><span className="font-bold text-blue-600 truncate max-w-[120px]">{window.TARGET_NAME}</span></div></div>
                        </div>
                    </div>
                    <div className="flex-1 flex flex-col h-full bg-[#f5f5f5] relative min-w-0">
                         <div className="h-16 bg-[#f5f5f5] border-b border-gray-200 flex items-center justify-between px-6 shrink-0 z-10"><div className="font-bold text-gray-700 text-lg">{messages.length > 0 ? `与 ${window.TARGET_NAME} 的聊天记录` : ""}</div></div>
                        <div className="flex-1 overflow-y-auto relative will-change-scroll" ref={scrollContainerRef} onScroll={onScroll}>
                            <div style={{ height: totalHeight, position: 'relative' }}>
                                <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${offsetY}px)`, padding: '20px 32px' }}>
                                    {visibleData.map((msg, localIndex) => {
                                        const realIndex = searchTerm ? localIndex : (startIndex + localIndex);
                                        const originalIndex = msg._originalIndex;
                                        let showDate = false;
                                        if (!searchTerm) { const prevMsg = filteredMessages[realIndex - 1]; showDate = realIndex === 0 || (prevMsg && prevMsg.date !== msg.date); }
                                        const isHighlighted = (msg.id || originalIndex) === highlightId;
                                        return (
                                            <React.Fragment key={msg.id || originalIndex}>
                                                {showDate && <div className="flex justify-center my-4"><span className="text-xs text-gray-400 bg-gray-200 px-2 py-1 rounded">{msg.date}</span></div>}
                                                <div className={`flex w-full mb-6 transition-colors duration-500 group/msg ${msg.isMe ? 'justify-end' : 'justify-start'} ${isHighlighted ? 'jump-highlight' : ''}`}>
                                                    {!msg.isMe && <div className="w-9 h-9 rounded bg-white flex items-center justify-center text-gray-400 mr-3 flex-shrink-0 shadow-sm border border-gray-100"><UserIcon /></div>}
                                                    <div className={`flex flex-col max-w-[70%] sm:max-w-[60%] ${msg.isMe ? 'items-end' : 'items-start'}`}>
                                                        <div className={`flex items-end gap-2 ${msg.isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                                                            <div className={`relative px-4 py-2.5 rounded-lg shadow-sm text-[15px] leading-relaxed break-words whitespace-pre-wrap ${msg.isMe ? 'bg-[#95ec69] text-black bubble-right' : 'bg-white text-gray-800 bubble-left'} ${msg.isRecalled ? 'recalled-bubble' : ''}`}>
                                                                {msg.type === '20001' ? <span className={msg.isRecalled ? "line-through text-gray-500" : ""}>{msg.content}</span> : <span className="italic text-gray-500 text-xs">[非文本: {msg.type}]</span>}
                                                            </div>
                                                            <span className="text-[10px] text-gray-400 mb-1 flex-shrink-0">{msg.short_time || msg.time.split(' ')[1]}</span>
                                                            {searchTerm && <button onClick={() => jumpToMessageContext(originalIndex, msg.id)} className="p-1.5 rounded-full bg-blue-100 text-blue-600 hover:bg-blue-200 transition opacity-0 group-hover/msg:opacity-100"><LocateIcon /></button>}
                                                        </div>
                                                    </div>
                                                </div>
                                            </React.Fragment>
                                        );
                                    })}
                                </div>
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
# 2. 后端核心逻辑
# ==========================================

def extract_and_parse_backup(file_path):
    """
    解析单个备份文件，返回 (db_path, temp_dir)
    """
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
                if newline_count == 4:
                    header_end_pos = i + 1; break
        
        header_lines = ab_data[:header_end_pos].split(b'\n')
        if len(header_lines) > 3 and header_lines[3].strip() != b'none':
            raise Exception("备份文件已加密，无法读取")

        is_compressed = True
        if len(header_lines) > 2:
             is_compressed = (header_lines[2].strip() == b'1')

        body_data = ab_data[header_end_pos:]
        try:
            tar_stream = zlib.decompress(body_data) if is_compressed else body_data
        except:
            tar_stream = body_data
        
        tar_path = os.path.join(temp_dir, 'backup.tar')
        with open(tar_path, 'wb') as f: f.write(tar_stream)
        
        target_suffix = 'apps/com.app.tideswing/db/TideSwing.db'
        found = False
        with tarfile.open(tar_path, 'r') as tar:
            target_member = None
            try: 
                target_member = tar.getmember(target_suffix)
            except KeyError:
                for member in tar.getmembers():
                    if member.name.endswith('TideSwing.db'): 
                        target_member = member; break
            
            if target_member:
                tar.extract(target_member, path=temp_dir)
                db_path = os.path.join(temp_dir, target_member.name)
                found = True
        
        if not found:
             raise Exception("未在备份包中找到 TideSwing.db")

        return db_path, temp_dir
    except Exception as e:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        raise e

def get_contact_list_from_db(db_path):
    contacts = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM t_user")
        rows = cursor.fetchall()
        for row in rows:
            uid, name = None, "未知用户"
            keys = row.keys()
            for k in ['user_id', 'USER_ID', 'id', 'ID', '_id']:
                if k in keys: uid = row[k]; break
            for k in ['nickname', 'NICKNAME', 'name', 'NAME']:
                if k in keys: name = row[k]; break
            if uid: contacts.append({"id": str(uid), "name": name}) 
        conn.close()
        return contacts
    except:
        return []

def query_chat_history_from_db(db_path, target_peer_id):
    """从单个DB查询消息，增加了极强的字段容错处理"""
    messages = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t_chat_msg'")
        if not cursor.fetchone():
            conn.close()
            return []

        cursor.execute("PRAGMA table_info(t_chat_msg)")
        columns = [col[1] for col in cursor.fetchall()]
        
        id_col = None
        for candidate in ['id', '_id', 'msg_id', 'ID', 'MSG_ID']:
            if candidate in columns:
                id_col = candidate; break
        
        content_col = 'content' if 'content' in columns else 'CONTENT'
        
        time_col = None
        for candidate in ['create_time', 'CREATE_TIME', 'time', 'TIME', 'timestamp']:
            if candidate in columns:
                time_col = candidate; break

        if not id_col or not time_col:
            conn.close(); return []

        query = f"SELECT * FROM t_chat_msg WHERE peer_user_id = ?"
        cursor.execute(query, (target_peer_id,))
        rows = cursor.fetchall()
        
        for row in rows:
            raw_id = row[id_col]
            msg_id = str(raw_id) if raw_id is not None else f"NOID_{row[time_col]}"
            content = row[content_col]
            create_time = row[time_col]
            
            msg_type = '1'
            if 'type' in columns: msg_type = row['type']
            elif 'TYPE' in columns: msg_type = row['TYPE']

            is_me = False
            keys = row.keys()
            if 'source' in keys: is_me = (row['source'] == 1)
            elif 'SOURCE' in keys: is_me = (row['SOURCE'] == 1)
            elif 'is_send' in keys: is_me = (row['is_send'] == 1)
                
            is_recalled = False
            if 'recall' in keys: is_recalled = (row['recall'] == 1)
            
            try:
                ts = float(create_time) / 1000.0
                dt = datetime.datetime.fromtimestamp(ts)
                full_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                date_str = dt.strftime('%Y-%m-%d')
                short_time = dt.strftime('%H:%M')
            except:
                full_time, date_str, short_time = "Unknown", "1970-01-01", "00:00"
                ts = 0

            messages.append({
                "id": msg_id, 
                "timestamp": ts, 
                "content": content,
                "time": full_time, 
                "short_time": short_time, 
                "date": date_str,
                "isMe": is_me, 
                "isRecalled": is_recalled, 
                "type": str(msg_type)
            })
        conn.close()
        return messages
    except Exception as e:
        print(f"Error querying db {db_path}: {e}")
        return []

# ==========================================
# 3. GUI 主程序
# ==========================================

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("可话记忆胶囊 - 桌面版")
        self.root.geometry("600x750") # 稍微调高一点高度，容纳顶部链接
        
        self.data_sources = [] 
        self.temp_dirs = []     
        self.contacts = []      
        self.current_display_contacts = [] 
        
        style = ttk.Style()
        style.configure("TButton", padding=5)
        
        # === 顶部：开源项目链接 ===
        frame_header = ttk.Frame(root)
        frame_header.pack(fill="x", padx=10, pady=10)
        
        lbl_title = ttk.Label(frame_header, text="✨ 如果觉得好用，请给个 Star 支持一下作者！", font=("Arial", 10, "bold"), foreground="#FF9800")
        lbl_title.pack(side="top", pady=(0, 5))

        link_frame = ttk.Frame(frame_header)
        link_frame.pack(side="top")

        # GitHub 链接
        lbl_github = tk.Label(link_frame, text="[GitHub]", font=("Arial", 9, "underline"), fg="blue", cursor="hand2")
        lbl_github.pack(side="left", padx=10)
        lbl_github.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/alicebob142857/kehua-chat-record-export"))
        
        # Gitee 链接
        lbl_gitee = tk.Label(link_frame, text="[Gitee]", font=("Arial", 9, "underline"), fg="red", cursor="hand2")
        lbl_gitee.pack(side="left", padx=10)
        lbl_gitee.bind("<Button-1>", lambda e: webbrowser.open("https://gitee.com/alicebob142857/kehua"))

        # === 第一步：多文件加载区 ===
        frame_top = ttk.LabelFrame(root, text="第一步：导入文件 (.ab / .bak / .db / .json)", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        self.file_listbox = tk.Listbox(frame_top, height=4, font=("Arial", 9), fg="#555")
        self.file_listbox.pack(side="left", fill="both", expand=True, padx=(0,5))
        
        btn_frame = ttk.Frame(frame_top)
        btn_frame.pack(side="right", fill="y")
        
        ttk.Button(btn_frame, text="➕ 添加文件", command=self.add_files).pack(fill="x", pady=(0,5))
        ttk.Button(btn_frame, text="🗑️ 清空列表", command=self.clear_files).pack(fill="x", pady=(0,5))
        self.btn_analyze = ttk.Button(btn_frame, text="🚀 开始解析", command=self.do_analyze_process, state="disabled")
        self.btn_analyze.pack(fill="x", side="bottom")

        # === 第二步：选择聊天对象 ===
        frame_mid = ttk.LabelFrame(root, text="第二步：选择聊天对象 (自动合并)", padding=10)
        frame_mid.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_contacts)
        
        search_frame = ttk.Frame(frame_mid)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="🔍 搜索昵称:", font=("Arial", 9)).pack(side="left")
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, state="disabled")
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(5,0))
        
        list_frame = ttk.Frame(frame_mid)
        list_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.contact_listbox = tk.Listbox(list_frame, height=10, selectmode="single", 
                                  exportselection=False, yscrollcommand=scrollbar.set,
                                  font=("Arial", 10))
        self.contact_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.contact_listbox.yview)
        self.contact_listbox.bind("<<ListboxSelect>>", self.on_select_change)

        # === 第三步：功能区 ===
        frame_action = ttk.Frame(root)
        frame_action.pack(pady=10, fill="x", padx=20)
        
        self.save_json_var = tk.BooleanVar(value=False)
        chk_json = ttk.Checkbutton(frame_action, text="同时导出合并后的 JSON 数据 (.json)", variable=self.save_json_var)
        chk_json.pack(anchor="w", pady=(0, 5))
        
        btn_box = ttk.Frame(frame_action)
        btn_box.pack(fill="x")

        self.btn_preview = ttk.Button(btn_box, text="👀 立即查看", command=self.do_preview, state="disabled")
        self.btn_preview.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=5)

        self.btn_export = ttk.Button(btn_box, text="💾 导出 HTML...", command=self.do_export, state="disabled")
        self.btn_export.pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=5)
        
        self.progress = ttk.Progressbar(root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(10, 0))

        self.lbl_status = ttk.Label(root, text="请先添加备份文件", foreground="gray")
        self.lbl_status.pack(side="bottom", pady=10)

    # ... (后面的 add_files, do_analyze_process 等所有方法完全保持不变，复制粘贴即可) ...
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Backup/JSON", "*.bak *.ab *.db *.json")])
        if not files: return
        
        count_added = 0
        for f in files:
            if f not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, f)
                count_added += 1
        
        if self.file_listbox.size() > 0:
            self.btn_analyze.config(state="normal")
            self.lbl_status.config(text=f"已准备 {self.file_listbox.size()} 个文件，点击“开始解析”", foreground="blue")

    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.btn_analyze.config(state="disabled")
        self.cleanup_temps()
        self.data_sources = []
        self.contacts = []
        self.update_contact_listbox([])
        self.lbl_status.config(text="列表已清空")
        self.progress['value'] = 0

    def do_analyze_process(self):
        raw_files = self.file_listbox.get(0, tk.END)
        if not raw_files: return
        
        self.lbl_status.config(text="正在解析文件...", foreground="orange")
        self.progress['value'] = 0
        self.progress['maximum'] = len(raw_files)
        self.root.update()
        
        self.cleanup_temps()
        self.data_sources = []
        
        valid_count = 0
        merged_contacts_dict = {}

        for i, f_path in enumerate(raw_files):
            try:
                ext = os.path.splitext(f_path)[1].lower()
                
                if ext == '.json':
                    with open(f_path, 'r', encoding='utf-8') as jf:
                        j_data = json.load(jf)
                        if isinstance(j_data, dict) and 'meta' in j_data:
                            meta = j_data['meta']
                            merged_contacts_dict[meta['id']] = {'id': meta['id'], 'name': meta['name']}
                            self.data_sources.append({'type': 'json', 'data': j_data})
                            valid_count += 1
                        else:
                            print(f"Skipping incompatible JSON: {f_path}")

                else:
                    db_path, temp_dir = extract_and_parse_backup(f_path)
                    self.temp_dirs.append(temp_dir)
                    self.data_sources.append({'type': 'db', 'path': db_path})
                    
                    c_list = get_contact_list_from_db(db_path)
                    for c in c_list:
                        merged_contacts_dict[c['id']] = c
                    valid_count += 1
            
            except Exception as e:
                print(f"File Error: {f_path} -> {e}")

            self.progress['value'] = i + 1
            self.root.update()
        
        self.contacts = list(merged_contacts_dict.values())
        
        if valid_count == 0:
            messagebox.showerror("错误", "所有文件均解析失败。")
            self.lbl_status.config(text="解析失败", foreground="red")
            return
        
        if not self.contacts:
             self.lbl_status.config(text="解析成功，但未发现联系人", foreground="orange")
             return

        self.update_contact_listbox(self.contacts)
        self.entry_search.config(state="normal")
        self.lbl_status.config(text=f"加载完成，共 {valid_count} 个有效源，{len(self.contacts)} 位联系人", foreground="green")

    def update_contact_listbox(self, contact_list):
        self.contact_listbox.delete(0, tk.END)
        self.current_display_contacts = contact_list
        for c in contact_list:
            display_text = c['name']
            self.contact_listbox.insert(tk.END, display_text)

    def filter_contacts(self, *args):
        keyword = self.search_var.get().lower()
        if not keyword: 
            self.update_contact_listbox(self.contacts)
            return
        filtered = [c for c in self.contacts if keyword in c['name'].lower()]
        self.update_contact_listbox(filtered)

    def on_select_change(self, event):
        selection = self.contact_listbox.curselection()
        if selection:
            self.btn_preview.config(state="normal")
            self.btn_export.config(state="normal")
        else:
            self.btn_preview.config(state="disabled")
            self.btn_export.config(state="disabled")

    def get_merged_messages(self, target_id):
        all_raw_messages = []
        
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.data_sources) + 1 
        
        for i, src in enumerate(self.data_sources):
            if src['type'] == 'db':
                msgs = query_chat_history_from_db(src['path'], target_id)
                all_raw_messages.extend(msgs)
            elif src['type'] == 'json':
                meta = src['data'].get('meta', {})
                if meta.get('id') == target_id:
                    all_raw_messages.extend(src['data'].get('messages', []))
            
            self.progress['value'] = i + 1
            self.root.update()

        if len(self.data_sources) == 1:
            all_raw_messages.sort(key=lambda x: x['timestamp'])
            for i, m in enumerate(all_raw_messages): m['_originalIndex'] = i
            return all_raw_messages

        id_map = {}
        for m in all_raw_messages:
            id_map[str(m['id'])] = m
        
        merged_list = list(id_map.values())
        merged_list.sort(key=lambda x: x['timestamp']) 
        
        final_unique_msgs = []
        if merged_list:
            final_unique_msgs.append(merged_list[0])
            for i in range(1, len(merged_list)):
                curr = merged_list[i]
                prev = final_unique_msgs[-1]
                
                time_match = abs(curr['timestamp'] - prev['timestamp']) < 0.001
                content_match = (curr['content'] == prev['content'])
                
                if time_match and content_match:
                    continue
                
                final_unique_msgs.append(curr)

        for i, m in enumerate(final_unique_msgs):
            m['_originalIndex'] = i
            
        self.progress['value'] = self.progress['maximum']
        self.root.update()
        
        return final_unique_msgs

    def generate_html_and_json(self, target_contact):
        target_id = target_contact['id']
        target_name = target_contact['name']
        
        messages = self.get_merged_messages(target_id)
        if not messages: return None, None, None

        json_str = json.dumps(messages, ensure_ascii=False)
        name_json = json.dumps(target_name, ensure_ascii=False)
        html_content = HTML_TEMPLATE.replace("__JSON_DATA_PLACEHOLDER__", json_str)
        html_content = html_content.replace("__TARGET_NAME_JSON__", name_json)

        json_data_full = {
            "meta": {
                "id": target_id,
                "name": target_name,
                "export_date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            "messages": messages
        }

        return html_content, json_data_full, len(messages)

    def do_preview(self):
        selection = self.contact_listbox.curselection()
        if not selection: return
        
        index = selection[0]
        contact = self.current_display_contacts[index]
        self.lbl_status.config(text="正在合并数据...", foreground="blue")

        try:
            html, _, count = self.generate_html_and_json(contact)
            if not html:
                messagebox.showinfo("提示", "无记录")
                self.lbl_status.config(text="无记录", foreground="gray")
                return

            temp_path = os.path.join(tempfile.gettempdir(), "kehua_preview.html")
            with open(temp_path, 'w', encoding='utf-8') as f: f.write(html)
            
            webbrowser.open('file://' + temp_path)
            self.lbl_status.config(text=f"预览已打开 (共 {count} 条)", foreground="green")

        except Exception as e:
            messagebox.showerror("错误", str(e))

    def do_export(self):
        selection = self.contact_listbox.curselection()
        if not selection: return
        
        index = selection[0]
        contact = self.current_display_contacts[index]
        
        default_name = f"可话_{contact['name']}_{datetime.datetime.now().strftime('%Y%m%d')}.html"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html")],
            initialfile=default_name,
            title="导出聊天记录"
        )
        if not save_path: return

        self.lbl_status.config(text="正在导出...", foreground="blue")
        try:
            html, json_data, count = self.generate_html_and_json(contact)
            
            if not html:
                messagebox.showinfo("提示", "无记录")
                return

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            msg = f"已导出 HTML 至: {save_path}"

            if self.save_json_var.get():
                json_path = os.path.splitext(save_path)[0] + ".json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                msg += f"\n及 JSON 至: {json_path}"

            self.lbl_status.config(text=f"导出成功 ({count} 条)", foreground="green")
            messagebox.showinfo("成功", msg)

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
    app = AppGUI(root)
    root.mainloop()
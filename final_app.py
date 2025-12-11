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
# 1. 前端模板 (包含安全注入修复)
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
        /* 安全注入数据，防止昵称包含特殊字符导致页面崩溃 */
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
    temp_dir = tempfile.mkdtemp()
    db_path = None
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.db': return file_path, temp_dir
        
        with open(file_path, 'rb') as f: raw_data = f.read()

        marker = b'ANDROID BACKUP'
        start_index = raw_data.find(marker)
        if start_index == -1 and ext != '.ab': raise Exception("不是有效的 Android 备份文件")
        ab_data = raw_data[start_index:] if start_index != -1 else raw_data

        header_end_pos = 0
        newline_count = 0
        for i in range(min(1000, len(ab_data))):
            if ab_data[i] == 10:
                newline_count += 1
                if newline_count == 4:
                    header_end_pos = i + 1; break
        
        header_lines = ab_data[:header_end_pos].split(b'\n')
        is_compressed = header_lines[2].strip() == b'1'
        if header_lines[3].strip() != b'none': raise Exception("备份已加密")

        body_data = ab_data[header_end_pos:]
        tar_stream = zlib.decompress(body_data) if is_compressed else body_data
        
        tar_path = os.path.join(temp_dir, 'backup.tar')
        with open(tar_path, 'wb') as f: f.write(tar_stream)
        
        target_suffix = 'apps/com.app.tideswing/db/TideSwing.db'
        with tarfile.open(tar_path, 'r') as tar:
            target_member = None
            try: target_member = tar.getmember(target_suffix)
            except KeyError:
                for member in tar.getmembers():
                    if member.name.endswith('TideSwing.db'): target_member = member; break
            if target_member:
                tar.extract(target_member, path=temp_dir)
                db_path = os.path.join(temp_dir, target_member.name)
            else: raise Exception("未找到 TideSwing.db")
        return db_path, temp_dir
    except Exception as e:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        raise e

def get_contact_list(db_path):
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
            if uid: contacts.append({"id": uid, "name": name})
        conn.close()
        return contacts
    except:
        return []

def query_chat_history(db_path, target_peer_id):
    messages = []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 防御性编程：先检查是否有数据
    try:
        cursor.execute("SELECT COUNT(*) FROM t_chat_msg WHERE peer_user_id = ?", (target_peer_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            conn.close()
            return [] 
    except:
        conn.close()
        return []

    query = "SELECT * FROM t_chat_msg WHERE peer_user_id = ? ORDER BY create_time ASC"
    cursor.execute(query, (target_peer_id,))
    rows = cursor.fetchall()
    
    for idx, row in enumerate(rows):
        keys = row.keys()
        _id = row['id'] if 'id' in keys else row['_id']
        content = row['content']
        create_time = row['create_time']
        msg_type = row['type']
        
        # =======================================================
        # 【关键修正】SOURCE = 1 是自己 (右侧)，其他是对方 (左侧)
        # =======================================================
        is_me = False
        if 'source' in keys:
            is_me = (row['source'] == 1)
        elif 'SOURCE' in keys:
            is_me = (row['SOURCE'] == 1)
        elif 'is_send' in keys:
            is_me = (row['is_send'] == 1)
            
        is_recalled = False
        if 'recall' in keys: is_recalled = (row['recall'] == 1)
        
        try:
            ts = float(create_time) / 1000.0
            dt = datetime.datetime.fromtimestamp(ts)
            full_time, date_str, short_time = dt.strftime('%Y-%m-%d %H:%M:%S'), dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M')
        except:
            full_time, date_str, short_time = "Unknown", "1970-01-01", "00:00"

        messages.append({
            "id": _id, "_originalIndex": idx, "content": content,
            "time": full_time, "short_time": short_time, "date": date_str,
            "isMe": is_me, "isRecalled": is_recalled, "type": str(msg_type)
        })
    conn.close()
    return messages

# ==========================================
# 3. GUI 主程序
# ==========================================

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("可话记忆胶囊 - 桌面版")
        self.root.geometry("500x450")
        
        self.db_path = None
        self.temp_dir = None
        self.contacts = []
        
        style = ttk.Style()
        style.configure("TButton", padding=5)

        # 步骤1：加载
        frame_top = ttk.LabelFrame(root, text="第一步：加载备份文件", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Entry(frame_top, textvariable=self.file_path).pack(side="left", fill="x", expand=True, padx=(0,5))
        ttk.Button(frame_top, text="浏览", command=self.browse_file).pack(side="right")
        self.btn_load = ttk.Button(frame_top, text="解析并加载联系人", command=self.do_load_process)
        self.btn_load.pack(side="bottom", fill="x", pady=(5,0))

        # 步骤2：选择
        frame_mid = ttk.LabelFrame(root, text="第二步：选择聊天对象", padding=10)
        frame_mid.pack(fill="x", padx=10, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_contacts)
        ttk.Label(frame_mid, text="搜索昵称:", font=("Arial", 9), foreground="gray").pack(anchor="w")
        self.entry_search = ttk.Entry(frame_mid, textvariable=self.search_var, state="disabled")
        self.entry_search.pack(fill="x", pady=(0, 5))
        
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(frame_mid, textvariable=self.combo_var, state="disabled")
        self.combo.pack(fill="x", pady=5)
        self.combo.bind("<<ComboboxSelected>>", self.on_select_change)

        # 步骤3：生成
        self.btn_gen = ttk.Button(root, text="生成聊天记录页面 (保存至桌面)", command=self.do_generate, state="disabled")
        self.btn_gen.pack(pady=20, ipadx=20, ipady=5)
        
        self.lbl_status = ttk.Label(root, text="就绪", foreground="gray")
        self.lbl_status.pack(side="bottom", pady=10)

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("Backup", "*.bak *.ab *.db")])
        if f: self.file_path.set(f)

    def do_load_process(self):
        f_path = self.file_path.get().strip()
        if not f_path or not os.path.exists(f_path):
            messagebox.showerror("错误", "文件无效")
            return
            
        self.lbl_status.config(text="处理中，请稍候...", foreground="orange")
        self.root.update()
        
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.db_path, self.temp_dir = extract_and_parse_backup(f_path)
            self.contacts = get_contact_list(self.db_path)
            
            if not self.contacts:
                messagebox.showwarning("提示", "未找到联系人数据")
                return

            self.update_combo_list(self.contacts)
            self.combo.config(state="readonly")
            self.entry_search.config(state="normal")
            self.lbl_status.config(text=f"加载成功，共 {len(self.contacts)} 人", foreground="green")
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.lbl_status.config(text="出错", foreground="red")

    def update_combo_list(self, contact_list):
        display_list = [f"{c['name']} ({c['id'][:6]}...)" for c in contact_list]
        self.combo['values'] = display_list
        if display_list: 
            self.combo.current(0)
            self.on_select_change(None)

    def filter_contacts(self, *args):
        keyword = self.search_var.get().lower()
        if not keyword: 
            self.update_combo_list(self.contacts)
            return
        filtered = [c for c in self.contacts if keyword in c['name'].lower() or keyword in c['id'].lower()]
        self.update_combo_list(filtered)

    def on_select_change(self, event):
        self.btn_gen.config(state="normal")

    def do_generate(self):
        current_display = self.combo.get()
        target_contact = None
        for c in self.contacts:
            if f"{c['name']} ({c['id'][:6]}...)" == current_display:
                target_contact = c
                break
        
        if not target_contact: return
        
        target_id = target_contact['id']
        target_name = target_contact['name']

        self.lbl_status.config(text=f"正在提取: {target_name}...", foreground="blue")
        self.root.update()

        try:
            messages = query_chat_history(self.db_path, target_id)
            
            if not messages or len(messages) == 0:
                messagebox.showinfo("无记录", f"与 {target_name} 没有聊天记录。")
                self.lbl_status.config(text="无记录", foreground="gray")
                return 

            # 生成 HTML 内容
            json_str = json.dumps(messages, ensure_ascii=False)
            name_json = json.dumps(target_name, ensure_ascii=False)
            
            html_content = HTML_TEMPLATE.replace("__JSON_DATA_PLACEHOLDER__", json_str)
            html_content = html_content.replace("__TARGET_NAME_JSON__", name_json)
            
            # ========================================================
            # 【关键修复】强制保存到桌面，解决 Read-only 报错
            # ========================================================
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            
            # 【关键修复】文件名只用安全的 ID，避免非法字符报错
            safe_filename = f"chat_{target_id[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.html"
            out_path = os.path.join(desktop_path, safe_filename)
            
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.lbl_status.config(text="已保存到桌面！", foreground="green")
            
            if os.path.exists(out_path):
                webbrowser.open('file://' + out_path)
            else:
                messagebox.showerror("错误", "文件生成失败，路径不存在")
            
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def __del__(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()
    
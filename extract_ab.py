
import os

def convert_miui_to_ab():
    print("--- 小米备份 .bak 转 .ab 工具 ---")
    
    # 获取当前目录下的所有 .bak 文件
    files = [f for f in os.listdir('.') if f.endswith('.bak')]
    if not files:
        print("❌ 未找到 .bak 文件")
        return

    # 简单起见，默认处理第一个找到的 bak 文件，或者你可以指定文件名
    filename = files[0] 
    print(f"正在处理文件: {filename}")
    
    output_filename = filename.replace('.bak', '.ab')
    
    try:
        with open(filename, 'rb') as f:
            content = f.read()
            
        # 核心逻辑：寻找 'ANDROID BACKUP' 字节序列的位置
        # 这就是标准 ab 文件的起始位置
        header_marker = b'ANDROID BACKUP'
        start_index = content.find(header_marker)
        
        if start_index == -1:
            print("❌ 错误：未在文件中找到 'ANDROID BACKUP' 标记。")
            print("可能这不是一个基于安卓原生备份的小米备份文件。")
            return
            
        print(f"✅ 找到标记，偏移量为: {start_index} 字节")
        print("正在切除头部并保存为 .ab 文件...")
        
        # 从该位置开始截取直到文件结束
        ab_content = content[start_index:]
        
        with open(output_filename, 'wb') as out_f:
            out_f.write(ab_content)
            
        print(f"\n🎉 成功！已生成文件: {output_filename}")
        print("👉 下一步：你需要使用 'Android Backup Extractor (abe)' 将此文件转换为 tar 包。")
        
    except Exception as e:
        print(f"❌ 处理出错: {e}")

if __name__ == "__main__":
    convert_miui_to_ab()

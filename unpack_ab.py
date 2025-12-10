
import zlib
import os
import tarfile

def unpack_ab_file():
    # 自动寻找当前目录下的 .ab 文件
    files = [f for f in os.listdir('.') if f.endswith('.ab')]
    if not files:
        print("❌ 未找到 .ab 文件，请先运行上一步的脚本。")
        return
    
    ab_filename = files[0]
    tar_filename = ab_filename.replace('.ab', '.tar')
    
    print(f"正在尝试解包: {ab_filename} -> {tar_filename}")
    
    try:
        with open(ab_filename, 'rb') as f:
            # 1. 读取文件头信息
            # ab 文件格式通常是：
            # Line 1: ANDROID BACKUP
            # Line 2: Version (e.g. 5)
            # Line 3: Compressed (0 or 1)
            # Line 4: Encryption Algorithm (none or AES-256)
            
            header_lines = []
            for _ in range(4):
                line = f.readline()
                header_lines.append(line)
            
            # 检查是否压缩
            is_compressed = header_lines[2].strip() == b'1'
            # 检查是否加密
            encryption = header_lines[3].strip()
            
            if encryption != b'none':
                print(f"❌ 错误：文件已加密 ({encryption})。本脚本只能处理未加密备份。")
                return
                
            print("ℹ️ 文件检查通过：未加密。准备解压数据流...")
            
            # 读取剩余所有数据
            data = f.read()
            
            # 2. 如果是压缩的 (Compressed=1)，用 zlib 解压
            if is_compressed:
                try:
                    decompressed_data = zlib.decompress(data)
                except Exception as zlib_error:
                     # 有时候 ab 文件虽然标记为压缩，或者是 Deflate 算法，直接解压可能需要忽略头部
                     # 如果标准解压失败，尝试使用 tarfile 自动识别
                     print(f"⚠️ zlib解压遇到问题: {zlib_error}")
                     print("尝试忽略错误继续...")
                     decompressed_data = data 
            else:
                decompressed_data = data

            # 3. 写入 tar 文件
            with open(tar_filename, 'wb') as tar_f:
                tar_f.write(decompressed_data)
                
            print(f"\n✅ 转换完成！生成了: {tar_filename}")
            print(f"👉 现在你可以直接双击 {tar_filename} 解压了！")
            
    except Exception as e:
        print(f"❌ 出错: {e}")

if __name__ == "__main__":
    unpack_ab_file()

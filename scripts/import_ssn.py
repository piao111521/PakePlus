import glob
import requests
import os
import time
import sys
from datetime import datetime

# 配置参数 (可通过环境变量覆盖)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost:8123")
DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")
TABLE = os.getenv("CLICKHOUSE_TABLE", "ssn_records")
SSN_PATTERN = os.getenv("SSN_FILE_PATTERN", "/mnt/e/ssn/ssn_out_*.txt")
EXPECTED_FILES = int(os.getenv("EXPECTED_FILE_COUNT", "188"))
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))
DELAY_BETWEEN_FILES = float(os.getenv("DELAY_BETWEEN_FILES", "0.3"))  # 秒


def test_clickhouse_connection():
    """测试ClickHouse连接"""
    try:
        response = requests.get(f"http://{CLICKHOUSE_HOST}/ping", timeout=10)
        if response.text == "Ok.\n":
            print("✅ ClickHouse连接正常")
            return True
        else:
            print(f"❌ ClickHouse响应异常: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ClickHouse连接失败: {str(e)}")
        return False


def find_ssn_files():
    """发现所有SSN文件"""
    files = sorted(glob.glob(SSN_PATTERN))
    print(f"发现 {len(files)} 个SSN文件")
    
    if len(files) == 0:
        print("❌ 未找到任何SSN文件")
        print(f"请检查路径: {SSN_PATTERN}")
        return []
    
    if len(files) != EXPECTED_FILES:
        print(f"⚠️ 警告: 发现 {len(files)} 个文件，期望 {EXPECTED_FILES} 个")
        
        # 显示前5个和后5个文件
        print(f"前5个文件: {files[:5]}")
        print(f"后5个文件: {files[-5:]}")
        
        continue_input = input("是否继续? (y/n): ")
        if continue_input.lower() != 'y':
            return []
    
    return files


def create_table_if_not_exists():
    """创建表结构"""
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {DATABASE}.{TABLE} (
        ID String, firstname String, lastname String, middlename String,
        name_suff String, dob String, address String, city String,
        county_name String, st String, zip String, phone1 String,
        aka1fullname String, aka2fullname String, aka3fullname String,
        StartDat String, alt1DOB String, alt2DOB String, alt3DOB String,
        ssn String
    ) ENGINE = MergeTree() ORDER BY ()
    """
    
    try:
        response = requests.post(
            f"http://{CLICKHOUSE_HOST}/",
            params={'query': create_sql},
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ 表 {DATABASE}.{TABLE} 创建成功")
            return True
        else:
            print(f"❌ 表创建失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 表创建异常: {str(e)}")
        return False


def import_single_file(file_path, retry_count=RETRY_COUNT):
    """导入单个文件，支持重试"""
    filename = os.path.basename(file_path)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return False, f"❌ {filename} - 文件不存在"
    
    # 获取文件大小
    try:
        file_size = os.path.getsize(file_path)
    except Exception as e:
        return False, f"❌ {filename} - 无法获取文件大小: {str(e)}"
    
    # 重试逻辑
    for attempt in range(retry_count):
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 发送到ClickHouse
            response = requests.post(
                f"http://{CLICKHOUSE_HOST}/",
                params={'query': f'INSERT INTO {DATABASE}.{TABLE} FORMAT CSV'},
                data=content,
                timeout=120
            )
            
            if response.status_code == 200:
                return True, f"✅ {filename} ({file_size:,} bytes)"
            else:
                error_msg = f"❌ {filename} - HTTP {response.status_code}: {response.text}"
                
                if attempt < retry_count - 1:
                    print(f"  重试 {attempt + 1}/{retry_count - 1}: {filename}")
                    time.sleep(2)
                    continue
                else:
                    return False, error_msg
                    
        except Exception as e:
            error_msg = f"❌ {filename} - {str(e)}"
            
            if attempt < retry_count - 1:
                print(f"  重试 {attempt + 1}/{retry_count - 1}: {filename}")
                time.sleep(2)
                continue
            else:
                return False, error_msg
    
    return False, f"❌ {filename} - 重试 {retry_count} 次均失败"


def import_all_files(files):
    """导入所有文件"""
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    print(f"🚀 开始导入 {len(files)} 个文件...")
    print("=" * 80)
    
    for i, file in enumerate(files):
        success, message = import_single_file(file)
        
        if success:
            success_count += 1
        else:
            error_count += 1
        
        print(f"{i+1:3d}/{len(files)}: {message}")
        
        # 进度报告
        if (i + 1) % 10 == 0 or (i + 1) == len(files):
            progress = (i + 1) / len(files) * 100
            elapsed = time.time() - start_time
            success_rate = success_count / (i + 1) * 100
            eta = elapsed * (len(files) - i - 1) / (i + 1)
            
            print(f"📊 进度: {progress:.1f}%, 成功率: {success_rate:.1f}%, 耗时: {elapsed:.1f}s, 预计剩余: {eta:.1f}s")
            print("-" * 80)
        
        # 延迟避免过快请求
        time.sleep(DELAY_BETWEEN_FILES)
    
    return success_count, error_count, time.time() - start_time


def verify_import():
    """验证导入结果"""
    print("🔍 验证导入结果...")
    
    try:
        # 获取总行数
        response = requests.post(
            f"http://{CLICKHOUSE_HOST}/",
            params={'query': f'SELECT COUNT(*) FROM {DATABASE}.{TABLE} FORMAT TabSeparated'},
            timeout=30
        )
        
        if response.status_code == 200:
            total_rows = int(response.text.strip())
            print(f"✅ 验证成功，总行数: {total_rows:,}")
            return total_rows
        else:
            print(f"❌ 验证查询失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 验证异常: {str(e)}")
        return None


def generate_final_report(success_count, error_count, total_time, total_rows):
    """生成最终报告"""
    total_files = success_count + error_count
    success_rate = success_count / total_files * 100
    
    print("\n" + "=" * 80)
    print("🎯 导入完成报告")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总文件数: {total_files}")
    print(f"成功导入: {success_count}")
    print(f"失败文件: {error_count}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"导入行数: {total_rows:,}" if total_rows else "导入行数: 未知")
    print(f"总耗时: {total_time:.1f}秒")
    
    if total_files > 0:
        avg_time_per_file = total_time / total_files
        print(f"平均每文件: {avg_time_per_file:.2f}秒")
    
    print("=" * 80)
    
    # 成功判断
    if success_rate >= 95 and total_rows and total_rows > 0:
        print("🎉 导入成功！")
        return True
    elif success_rate >= 90:
        print("⚠️ 导入基本成功，但有一些问题")
        return True
    else:
        print("❌ 导入未成功，请检查错误信息")
        return False


def main():
    """主执行函数"""
    print("=" * 80)
    print("🚀 SSN数据批量导入工具")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"目标: {EXPECTED_FILES} 个SSN文件")
    print(f"数据库: {DATABASE}.{TABLE}")
    
    # 环境检查
    print("\n📋 环境检查...")
    if not test_clickhouse_connection():
        print("❌ ClickHouse连接失败，程序退出")
        return False
    
    # 发现文件
    print("\n🔍 发现文件...")
    files = find_ssn_files()
    if not files:
        print("❌ 未找到可用的SSN文件，程序退出")
        return False
    
    # 创建表
    print("\n🏗️ 检查表结构...")
    if not create_table_if_not_exists():
        print("❌ 表结构创建失败，程序退出")
        return False
    
    # 执行导入
    print("\n📦 开始批量导入...")
    success_count, error_count, total_time = import_all_files(files)
    
    # 验证结果
    print("\n🔍 验证导入结果...")
    total_rows = verify_import()
    
    # 生成报告
    print("\n📊 生成最终报告...")
    success = generate_final_report(success_count, error_count, total_time, total_rows)
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断导入")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 程序异常: {str(e)}")
        sys.exit(1)

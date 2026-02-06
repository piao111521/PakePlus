# SSN Data Import Tool for ClickHouse

## Overview

This script is designed to batch import SSN (Social Security Number) data files into a ClickHouse database. It provides comprehensive features including connection testing, file discovery, retry logic, progress reporting, and verification.

## Features

✅ **Robust Features:**
- **Automatic Retry**: Each file is retried up to 3 times on failure
- **Detailed Progress**: Reports progress every 10 files
- **Complete Verification**: Automatically verifies row counts after import
- **Error Isolation**: Single file failures don't affect the entire import process
- **User Friendly**: Clear, formatted output with emoji indicators
- **Interrupt Recovery**: Supports Ctrl+C interruption

## Configuration Parameters

The script can be configured by modifying these parameters at the top of the file:

```python
CLICKHOUSE_HOST = "localhost:8123"      # ClickHouse server address
DATABASE = "default"                    # Target database name
TABLE = "ssn_records"                   # Target table name
SSN_PATTERN = "/mnt/e/ssn/ssn_out_*.txt"  # File pattern for SSN files
EXPECTED_FILES = 188                    # Expected number of files
RETRY_COUNT = 3                         # Number of retry attempts per file
DELAY_BETWEEN_FILES = 0.3              # Delay in seconds between file imports
```

## Prerequisites

1. **Python Dependencies**: Install required packages
   ```bash
   pip install requests
   ```

2. **ClickHouse Server**: Ensure ClickHouse is running and accessible at the configured host

3. **SSN Data Files**: Place your SSN data files in the specified directory

## Usage

### Basic Usage

```bash
python scripts/import_ssn.py
```

### Configuration Steps

1. **Update File Pattern**: Modify `SSN_PATTERN` to match your file location
   ```python
   SSN_PATTERN = "/path/to/your/ssn/ssn_out_*.txt"
   ```

2. **Configure ClickHouse**: Update host if not using default
   ```python
   CLICKHOUSE_HOST = "your-clickhouse-host:8123"
   ```

3. **Adjust Expected Files**: Set the expected number of files
   ```python
   EXPECTED_FILES = 188  # Change to your expected count
   ```

## Table Schema

The script creates the following table structure:

```sql
CREATE TABLE IF NOT EXISTS default.ssn_records (
    ID String,
    firstname String,
    lastname String,
    middlename String,
    name_suff String,
    dob String,
    address String,
    city String,
    county_name String,
    st String,
    zip String,
    phone1 String,
    aka1fullname String,
    aka2fullname String,
    aka3fullname String,
    StartDat String,
    alt1DOB String,
    alt2DOB String,
    alt3DOB String,
    ssn String
) ENGINE = MergeTree() ORDER BY ()
```

## Output Example

```
================================================================================
🚀 SSN数据批量导入工具
================================================================================
开始时间: 2024-01-15 10:30:00
Python版本: 3.9.0
目标: 188 个SSN文件
数据库: default.ssn_records

📋 环境检查...
✅ ClickHouse连接正常

🔍 发现文件...
发现 188 个SSN文件

🏗️ 检查表结构...
✅ 表 default.ssn_records 创建成功

📦 开始批量导入...
🚀 开始导入 188 个文件...
================================================================================
  1/188: ✅ ssn_out_001.txt (1,234,567 bytes)
  2/188: ✅ ssn_out_002.txt (1,234,890 bytes)
...
 10/188: ✅ ssn_out_010.txt (1,235,123 bytes)
📊 进度: 5.3%, 成功率: 100.0%, 耗时: 30.5s, 预计剩余: 543.0s
--------------------------------------------------------------------------------
...
```

## Error Handling

The script handles various error scenarios:

- **Connection Failures**: Tests ClickHouse connection before starting
- **Missing Files**: Validates file existence before import
- **Import Errors**: Retries failed imports with exponential backoff
- **User Interruption**: Gracefully handles Ctrl+C

## Exit Codes

- `0`: Success (≥95% success rate with rows imported)
- `1`: Failure or user interruption

## Troubleshooting

### ClickHouse Connection Failed
- Verify ClickHouse is running
- Check the host and port configuration
- Ensure network connectivity

### No Files Found
- Verify the `SSN_PATTERN` path is correct
- Check file permissions
- Ensure files match the pattern (e.g., `ssn_out_*.txt`)

### Import Failures
- Check ClickHouse logs for errors
- Verify file format matches expected CSV structure
- Ensure sufficient disk space on ClickHouse server

## Security Considerations

- This script handles sensitive SSN data - ensure proper security measures
- Use secure connections in production (consider HTTPS for ClickHouse)
- Implement proper access controls for the ClickHouse database
- Do not commit actual SSN data files to version control

## License

This script is part of the PakePlus project and follows the same license terms.

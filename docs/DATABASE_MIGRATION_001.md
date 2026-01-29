# 数据库迁移 #001: 图片ID改为自增并添加MD5/SHA256

## 概述

本次迁移对 `images` 表进行了重大更改：
1. 将图片ID从MD5哈希值改为数据库自增整数
2. 添加单独的 `md5` 和 `sha256` 字段用于文件去重
3. 保持向后兼容，旧数据的MD5值会被迁移到新的 `md5` 字段

## 更改详情

### 之前（旧结构）

```sql
CREATE TABLE images (
    id VARCHAR(32) PRIMARY KEY,  -- 使用MD5作为ID
    original_filename VARCHAR(255) NOT NULL,
    storage_filename VARCHAR(500) NOT NULL,
    storage_engine_id INTEGER NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    width INTEGER,
    height INTEGER,
    upload_ip VARCHAR(45),
    extra_metadata JSON,
    original_url TEXT NOT NULL,
    thumbnail_url TEXT,
    is_deleted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(storage_engine_id) REFERENCES storage_engines(id)
);
```

### 之后（新结构）

```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增ID
    md5 VARCHAR(32) NOT NULL,  -- 新增：MD5哈希
    sha256 VARCHAR(64) NOT NULL,  -- 新增：SHA256哈希
    original_filename VARCHAR(255) NOT NULL,
    storage_filename VARCHAR(500) NOT NULL,
    storage_engine_id INTEGER NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    width INTEGER,
    height INTEGER,
    upload_ip VARCHAR(45),
    extra_metadata JSON,
    original_url TEXT NOT NULL,
    thumbnail_url TEXT,
    is_deleted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(storage_engine_id) REFERENCES storage_engines(id)
);
```

### 新增索引

```sql
CREATE INDEX ix_images_md5 ON images (md5);
CREATE INDEX ix_images_sha256 ON images (sha256);
```

## 迁移步骤

### 1. 执行升级

```bash
# 使用Alembic执行迁移
alembic upgrade head
```

迁移过程：
1. 创建新的 `images_new` 表，包含新的结构
2. 将旧表的数据复制到新表：
   - 旧的 `id`（MD5）→ 新的 `md5` 字段
   - 旧的 `id`（MD5）→ 新的 `sha256` 字段（临时相同）
3. 删除旧的 `images` 表
4. 将 `images_new` 重命名为 `images`
5. 重建所有索引

### 2. 验证迁移

```sql
-- 检查表结构
.schema images

-- 检查数据完整性
SELECT COUNT(*) FROM images;

-- 检查MD5字段
SELECT id, md5, sha256 FROM images LIMIT 5;
```

### 3. 回滚（如需要）

```bash
# 回滚迁移
alembic downgrade base
```

## API变更

### 请求参数变更

| 端点 | 参数类型 | 之前 | 之后 |
|------|---------|------|------|
| GET `/api/v1/images/{image_id}` | image_id | `string` (MD5) | `integer` |
| DELETE `/api/v1/images/{image_id}` | image_id | `string` (MD5) | `integer` |
| POST `/api/v1/images/batch-delete` | image_ids | `List[string]` | `List[integer]` |

### 响应字段变更

#### ImageResponse / ImageUploadResponse

新增字段：
```json
{
  "id": 123,  // 改为整数
  "md5": "d41d8cd98f00b204e9800998ecf8427e",  // 新增
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  // 新增
  "filename": "image.jpg",
  "url": "http://example.com/uploads/image.jpg",
  "size": 102400,
  "width": 1920,
  "height": 1080
}
```

## 代码变更

### 1. 模型层 (`app/models/image.py`)

```python
class Image(Base):
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, index=True
    )
    md5: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # ... 其他字段 ...
```

### 2. 服务层 (`app/services/image.py`)

```python
# 上传时计算两个哈希值
md5_hash = calculate_md5(file_data)
sha256_hash = calculate_sha256(file_data)

# 通过MD5或SHA256检查重复
existing_image = await db.execute(
    select(Image).where(
        (Image.md5 == md5_hash) | (Image.sha256 == sha256_hash)
    ).where(Image.is_deleted == False)
)

# 创建新记录（使用自增ID）
image = Image(
    md5=md5_hash,
    sha256=sha256_hash,
    # ... 其他字段 ...
)
```

### 3. 工具函数 (`app/utils/file.py`)

```python
def calculate_md5(data: bytes) -> str:
    """计算文件的MD5哈希值"""
    return hashlib.md5(data).hexdigest()

def calculate_sha256(data: bytes) -> str:
    """计算文件的SHA256哈希值"""
    return hashlib.sha256(data).hexdigest()
```

## 文件去重逻辑

新的去重机制：

```python
# 上传新图片时
1. 计算MD5和SHA256
2. 查询数据库：
   SELECT * FROM images 
   WHERE (md5 = 'xxx' OR sha256 = 'yyy') 
   AND is_deleted = FALSE
3. 如果找到匹配记录，返回现有图片
4. 否则，创建新记录并上传
```

### 优势

1. **双重哈希验证**：同时使用MD5和SHA256，降低碰撞概率
2. **更好的性能**：
   - 自增ID查询更快
   - 可以在索引上高效查询
3. **更灵活的存储**：SHA256提供更强的安全性
4. **向后兼容**：旧数据不会被丢失

## 注意事项

### 1. API兼容性

**破坏性变更**：所有使用MD5作为图片ID的API调用都需要更新

**示例**：
```bash
# 之前（错误）
curl http://localhost:8000/api/v1/images/d41d8cd98f00b204e9800998ecf8427e

# 之后（正确）
curl http://localhost:8000/api/v1/images/123
```

### 2. 客户端更新

如果您的客户端代码硬编码了图片ID（MD5），需要：

1. 获取所有图片列表，建立ID映射
2. 更新数据库中的引用
3. 更新API调用代码

### 3. 数据备份

在执行迁移前，建议备份数据库：

```bash
# SQLite
cp db/database.db db/database.db.backup

# 或者使用SQL导出
sqlite3 db/database.db .dump > backup.sql
```

### 4. 性能考虑

- **MD5索引**：32字符，快速查询
- **SHA256索引**：64字符，提供更强的唯一性保证
- **自增ID**：插入性能略低于MD5 ID（需要计算哈希），但查询更快

## 测试建议

### 1. 单元测试

```python
async def test_image_upload():
    # 上传图片
    response = await client.post("/api/v1/images/upload", files={"file": test_image})
    assert response.status_code == 201
    
    data = response.json()["data"]
    assert isinstance(data["id"], int)  # ID是整数
    assert "md5" in data
    assert "sha256" in data
    
    # 重新上传相同图片（应该去重）
    response2 = await client.post("/api/v1/images/upload", files={"file": test_image})
    assert response2.json()["data"]["id"] == data["id"]  # 返回相同ID
```

### 2. 集成测试

```bash
# 1. 上传图片
curl -X POST http://localhost:8000/api/v1/images/upload \
  -F "file=@test.jpg"

# 2. 获取图片列表
curl http://localhost:8000/api/v1/images

# 3. 通过ID获取图片
curl http://localhost:8000/api/v1/images/1

# 4. 删除图片
curl -X DELETE http://localhost:8000/api/v1/images/1
```

## 故障排查

### 问题1：迁移失败

**错误信息**：
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table images already exists
```

**解决方案**：
```bash
# 手动检查数据库
sqlite3 db/database.db ".schema images"

# 如果表已存在，先删除旧表
# 注意：这会丢失数据！
sqlite3 db/database.db "DROP TABLE IF EXISTS images"

# 重新运行迁移
alembic upgrade head
```

### 问题2：数据丢失

**症状**：迁移后图片记录变少

**检查**：
```sql
-- 检查数据是否在临时表中
SELECT COUNT(*) FROM images_new;

-- 查看迁移日志
```

**解决方案**：
1. 从备份恢复
2. 检查迁移脚本
3. 手动执行SQL

### 问题3：API返回404

**症状**：使用旧ID无法访问图片

**原因**：旧客户端使用MD5作为ID

**解决方案**：
- 更新客户端代码使用新ID
- 或者提供迁移工具批量更新客户端数据

## 总结

本次迁移的主要改进：

✅ **ID改为自增**：更符合数据库最佳实践，查询性能更好
✅ **双哈希验证**：MD5 + SHA256，提供更强的唯一性保证
✅ **向后兼容**：旧数据会被正确迁移
✅ **更好的去重**：通过两个字段进行文件去重
✅ **更安全**：SHA256提供更强的安全性

⚠️ **破坏性变更**：API参数类型从string改为int，需要更新客户端

⚠️ **需要测试**：在生产环境部署前充分测试

## 相关文档

- [数据库迁移指南](./DATABASE_MIGRATION.md)
- [API文档](./API.md)
- [存储引擎缓存指南](./STORAGE_CACHE_GUIDE.md)

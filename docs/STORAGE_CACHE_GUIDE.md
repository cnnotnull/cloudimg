# 存储引擎缓存机制使用指南

## 概述

CloudImage系统实现了存储引擎缓存机制，将数据库中激活的存储引擎在应用启动时加载到内存中，避免每次操作都查询数据库和重新创建存储实例，从而显著提升性能。

## 核心特性

### 1. 自动初始化
- 应用启动时自动加载所有激活的存储引擎
- 自动识别并设置默认存储引擎
- 初始化失败不会影响应用启动，会记录错误日志

### 2. 实时同步
- 创建存储引擎：自动添加到缓存（如果激活）
- 更新存储引擎：自动更新缓存
- 删除存储引擎：自动从缓存移除
- 设置默认存储引擎：自动更新缓存中的默认标记

### 3. 高效访问
- 通过缓存直接获取存储实例，无需数据库查询
- 支持获取默认存储引擎
- 支持获取特定存储引擎

## 架构设计

### 缓存结构

```python
{
    storage_id: {
        "engine": StorageEngine,      # 数据库模型对象
        "instance": StorageBase       # 存储引擎实例
    }
}
```

### 单例模式

`StorageCache` 使用单例模式，确保整个应用只有一个缓存实例：

```python
from app.core.storage_cache import storage_cache
```

### 缓存生命周期

1. **启动时加载**
   ```python
   # app/main.py - lifespan函数
   async for db in get_db():
       await storage_cache.initialize(db)
       break
   ```

2. **运行时更新**
   - 通过 StorageService 的方法自动同步缓存
   - 创建、更新、删除存储引擎时自动触发

3. **关闭时清理**
   ```python
   # app/main.py - lifespan函数
   storage_cache.clear()
   ```

## 使用方法

### 1. 获取存储引擎实例

```python
from app.core.storage_cache import storage_cache

# 获取指定存储引擎实例
storage_instance = storage_cache.get_storage(storage_id)

# 获取默认存储引擎实例
default_storage = storage_cache.get_default_storage()

# 获取所有存储引擎实例
all_storages = storage_cache.get_all_storages()
```

### 2. 获取存储引擎配置

```python
from app.core.storage_cache import storage_cache

# 获取指定存储引擎配置对象
storage_engine = storage_cache.get_storage_engine(storage_id)

# 获取默认存储引擎配置对象
default_engine = storage_cache.get_default_storage_engine()

# 获取所有存储引擎配置对象
all_engines = storage_cache.get_all_storage_engines()
```

### 3. 检查存储引擎是否存在

```python
from app.core.storage_cache import storage_cache

# 检查存储引擎是否在缓存中
exists = storage_cache.storage_exists(storage_id)
```

### 4. 查看缓存信息

```python
from app.core.storage_cache import storage_cache

# 获取缓存信息
cache_info = storage_cache.get_cache_info()
# 返回:
# {
#     "total_count": 3,
#     "default_storage_id": 1,
#     "storage_ids": [1, 2, 3],
#     "storage_types": {1: "local", 2: "s3", 3: "s3"}
# }
```

## API端点

### 获取缓存信息（调试用）

**端点：** `GET /cache/info`

**说明：** 获取当前存储引擎缓存的详细信息，仅在DEBUG模式下可用。

**响应示例：**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "total_count": 2,
    "default_storage_id": 1,
    "storage_ids": [1, 2],
    "storage_types": {
      "1": "local",
      "2": "s3"
    }
  }
}
```

**使用场景：**
- 调试时查看缓存的存储引擎状态
- 验证存储引擎是否正确加载
- 检查默认存储引擎设置

## 集成示例

### 在Service中使用缓存

#### ImageService 示例

```python
from app.core.storage_cache import storage_cache

async def upload_image(file: UploadFile, storage_engine_id: int = None):
    # 获取存储引擎配置
    storage = await StorageService.get_by_id(db, storage_engine_id)
    
    # 从缓存获取存储实例
    storage_instance = storage_cache.get_storage(storage.id)
    if not storage_instance:
        raise AppException(
            status_code=500,
            detail="存储引擎实例未加载到缓存"
        )
    
    # 使用存储实例上传文件
    url = await storage_instance.upload(file_data, storage_path)
```

#### StorageService 示例

```python
from app.core.storage_cache import storage_cache

async def create_storage(db: AsyncSession, storage_data: dict):
    # 创建存储引擎记录
    storage = StorageEngine(**storage_data)
    db.add(storage)
    await db.commit()
    
    # 添加到缓存
    if storage.is_active:
        storage_cache.add_storage(storage)
    
    return storage

async def update_storage(db: AsyncSession, storage_id: int, storage_data: dict):
    # 更新数据库记录
    storage = await StorageService.get_by_id(db, storage_id)
    for key, value in storage_data.items():
        setattr(storage, key, value)
    await db.commit()
    
    # 更新缓存
    storage_cache.update_storage(storage)
    
    return storage

async def delete_storage(db: AsyncSession, storage_id: int):
    # 从缓存删除
    storage_cache.delete_storage(storage_id)
    
    # 删除数据库记录
    await db.delete(storage)
    await db.commit()
```

### 在API路由中使用缓存

```python
from app.core.storage_cache import storage_cache

@router.post("/{storage_id}/test")
async def test_storage_engine(storage_id: int):
    # 从缓存获取存储实例
    storage_instance = storage_cache.get_storage(storage_id)
    if not storage_instance:
        raise HTTPException(status_code=404, detail="存储引擎未加载")
    
    # 测试连接
    success = await storage_instance.test_connection()
    
    return {"success": success}
```

## 缓存同步机制

### 创建存储引擎

```python
# StorageService.create()
storage = StorageEngine(...)
db.add(storage)
await db.commit()

# 如果激活，自动添加到缓存
if storage.is_active:
    storage_cache.add_storage(storage)
```

### 更新存储引擎

```python
# StorageService.update()
storage = await StorageService.get_by_id(db, storage_id)
# ... 更新字段 ...
await db.commit()

# 自动更新缓存
storage_cache.update_storage(storage)
```

### 删除存储引擎

```python
# StorageService.delete()
# 先从缓存删除
storage_cache.delete_storage(storage_id)

# 再删除数据库记录
await db.delete(storage)
await db.commit()
```

### 设置默认存储引擎

```python
# StorageService.set_default()
await db.execute(
    update(StorageEngine).where(StorageEngine.id != storage_id).values(is_default=False)
)
storage.is_default = True
await db.commit()

# 更新缓存中的默认标记
storage_cache.update_default_storage(storage_id)
```

## 性能优势

### 1. 减少数据库查询
- **无缓存：** 每次上传图片都查询数据库获取存储引擎配置
- **有缓存：** 启动时加载一次，后续直接从内存读取

### 2. 避免重复创建实例
- **无缓存：** 每次操作都创建新的存储引擎实例（包括S3客户端等）
- **有缓存：** 实例复用，减少资源消耗

### 3. 提升响应速度
- **数据库查询：** ~10-50ms
- **内存访问：** <1ms
- **性能提升：** 10-50倍

## 最佳实践

### 1. 始终通过StorageService操作数据库

```python
# ✓ 推荐：通过Service操作
storage = await StorageService.create(db, storage_data)

# ✗ 不推荐：直接操作数据库
storage = StorageEngine(**storage_data)
db.add(storage)
await db.commit()
# 缓存不会自动更新！
```

### 2. 优先使用缓存获取存储实例

```python
# ✓ 推荐：从缓存获取
storage_instance = storage_cache.get_storage(storage_id)

# ✗ 不推荐：每次都创建新实例
storage_engine = await StorageService.get_by_id(db, storage_id)
storage_instance = StorageFactory.create(storage_engine.type, storage_engine.config)
```

### 3. 异常处理

```python
storage_instance = storage_cache.get_storage(storage_id)
if not storage_instance:
    # 缓存中不存在，可能是：
    # 1. 存储引擎未激活
    # 2. 存储引擎已被删除
    # 3. 缓存未正确初始化
    raise AppException(
        status_code=500,
        detail="存储引擎实例未加载",
        error_code="STORAGE_NOT_LOADED"
    )
```

### 4. 调试时查看缓存状态

```python
# 开发环境：访问 /cache/info 端点
# 生产环境：查看应用日志中的缓存初始化信息
```

## 故障排查

### 1. 缓存未正确初始化

**症状：** 所有存储引擎操作都失败

**检查：**
```python
# 查看启动日志
[CACHE] 正在初始化存储引擎缓存...
[CACHE] ✓ 加载存储引擎: 本地存储 (ID: 1, 类型: local)
[CACHE] ✓ 加载存储引擎: AWS S3 (ID: 2, 类型: s3)
[CACHE] 存储引擎缓存初始化完成，共加载 2 个存储引擎
```

**解决：** 检查数据库中是否有激活的存储引擎

### 2. 存储引擎未加载到缓存

**症状：** `storage_cache.get_storage(storage_id)` 返回None

**检查：**
```bash
# 查看缓存信息
curl http://localhost:8000/cache/info
```

**原因：**
- 存储引擎未激活 (`is_active=False`)
- 存储引擎配置有误，创建实例失败
- 存储引擎被删除

**解决：**
```python
# 检查存储引擎状态
storage = await StorageService.get_by_id(db, storage_id)
print(f"is_active: {storage.is_active}")
print(f"is_default: {storage.is_default}")

# 如果未激活，激活它
storage.is_active = True
await db.commit()
```

### 3. 缓存与数据库不同步

**症状：** 修改了存储引擎配置但操作仍使用旧配置

**检查：**
```python
# 查看启动日志中的初始化信息
# 检查是否有缓存更新日志
[CACHE] ✓ 更新存储引擎: AWS S3 (ID: 2, 激活: True)
```

**解决：**
- 确保通过 StorageService 操作数据库
- 检查更新操作是否成功提交
- 查看是否有异常被捕获

### 4. S3存储引擎连接失败

**症状：** 启动时显示加载失败

**日志：**
```
[CACHE] ✗ 加载存储引擎失败: AWS S3 (ID: 2), 错误: ...
```

**解决：**
- 检查S3配置是否正确
- 验证访问密钥和region
- 确认网络连接正常
- 检查bucket是否存在

## 监控和维护

### 1. 监控缓存状态

定期检查缓存信息：
```python
# 添加定时任务检查缓存状态
@app.on_event("startup")
async def setup_cache_monitoring():
    import asyncio
    
    async def monitor_cache():
        while True:
            cache_info = storage_cache.get_cache_info()
            logger.info(f"Cache status: {cache_info}")
            await asyncio.sleep(300)  # 每5分钟
    
    asyncio.create_task(monitor_cache())
```

### 2. 缓存重载

如果需要重新加载缓存（不重启应用）：
```python
from app.config.database import get_db

async def reload_cache():
    async for db in get_db():
        await storage_cache.initialize(db)
        break
```

### 3. 日志级别

生产环境建议：
```python
# app/main.py
import logging

logging.getLogger("app.core.storage_cache").setLevel(logging.INFO)
```

## 总结

存储引擎缓存机制提供了：
- ✅ 自动初始化和同步
- ✅ 高效的内存访问
- ✅ 减少数据库查询
- ✅ 避免重复创建实例
- ✅ 显著的性能提升

遵循最佳实践，确保：
- 通过 StorageService 操作数据库
- 优先使用缓存获取存储实例
- 妥善处理缓存不存在的情况
- 定期检查缓存状态

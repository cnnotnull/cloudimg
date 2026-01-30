# 数据库迁移指南

本文档介绍如何使用Alembic进行数据库迁移管理。

## 概述

项目已从`init_db()`方法迁移到Alembic进行数据库管理。Alembic是一个轻量级的数据库迁移工具，可以帮助你管理数据库结构的变更历史。

## 安装依赖

确保已安装alembic：

```bash
uv add alembic
```

## 配置说明

Alembic配置文件：
- `alembic.ini` - Alembic主配置文件
- `migrations/env.py` - 迁移环境配置
- `migrations/versions/` - 迁移脚本存储目录

## 迁移工作流程

### 1. 创建新迁移

当修改了数据库模型（在`app/models/`目录下）后，需要创建新的迁移：

```bash
# 自动生成迁移（推荐）
alembic revision --autogenerate -m "描述信息"

# 示例
alembic revision --autogenerate -m "Add email field to user"
```

`--autogenerate`参数会自动检测模型变化并生成迁移脚本。

### 2. 查看迁移状态

查看当前迁移状态：

```bash
alembic current
```

查看迁移历史：

```bash
alembic history
```

### 3. 执行迁移

应用所有未执行的迁移：

```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision_id>

# 示例
alembic upgrade 4a16a841224e
```

### 4. 回滚迁移

回滚到之前的版本：

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>

# 回滚到初始状态
alembic downgrade base
```

## 首次部署

### 1. 删除现有数据库（如果需要）

```bash
# 删除数据库文件
rm db/database.db

# 或者
del db\database.db
```

### 2. 执行迁移

```bash
# 应用所有迁移
alembic upgrade head
```

### 3. 验证数据库

检查数据库表是否正确创建：

```bash
# 使用SQLite命令行工具
sqlite3 db/database.db
sqlite> .tables
sqlite> .schema storage_engines
sqlite> .quit
```

## 开发环境使用

在开发环境中修改模型后：

1. **修改模型文件**（在`app/models/`目录下）

2. **创建迁移**：
   ```bash
   alembic revision --autogenerate -m "描述变更"
   ```

3. **检查迁移脚本**：
   在`migrations/versions/`目录下查看生成的迁移脚本
   
4. **应用迁移**：
   ```bash
   alembic upgrade head
   ```

5. **重启应用**验证变更

## 生产环境使用

在生产环境中：

1. **先在测试环境验证迁移**
2. **备份数据库**
3. **应用迁移**：
   ```bash
   alembic upgrade head
   ```
4. **验证应用正常运行**

## 迁移脚本示例

自动生成的迁移脚本示例：

```python
"""Add new column

Revision ID: abc123
Revises: 
Create Date: 2024-01-30 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abc123'
down_revision = None  # 或上一版本的ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 升级操作
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # 降级操作
    op.drop_column('users', 'email')
```

## 常见问题

### 1. 迁移失败

如果迁移执行失败：

```bash
# 查看当前版本
alembic current

# 查看错误日志
# 错误信息会显示在终端

# 修复问题后，可以继续
alembic upgrade head
```

### 2. 自动生成的迁移不正确

如果自动生成的迁移不符合预期：

1. 可以手动编辑迁移脚本
2. 或者不使用`--autogenerate`，手动创建迁移：
   ```bash
   alembic revision -m "手动描述"
   ```
3. 然后手动编写`upgrade()`和`downgrade()`函数

### 3. 多个开发者同时创建迁移

如果多个开发者同时创建了迁移：

```bash
# 使用--splice参数合并分支
alembic merge -m "合并迁移" <revision1> <revision2>
```

### 4. 数据库已存在数据

如果数据库已有数据，需要小心处理：

- 检查迁移脚本是否会影响现有数据
- 在`downgrade()`函数中确保数据可以恢复
- 在执行前备份数据库

## 迁移最佳实践

1. **保持迁移独立**：每个迁移应该可以独立执行
2. **提供降级路径**：确保每个迁移都可以回滚
3. **使用描述性消息**：使用清晰的迁移描述
4. **测试迁移**：在生产环境前先在测试环境验证
5. **版本控制**：将迁移脚本纳入版本控制
6. **定期清理**：删除不再需要的旧迁移版本

## 现有模型

项目包含以下模型：

- `app/models/storage.py` - 存储引擎模型
- `app/models/image.py` - 图片模型
- `app/models/config.py` - 系统配置模型

## 从旧系统迁移

如果你之前使用`init_db()`方法：

1. **备份数据库**：
   ```bash
   cp db/database.db db/database.db.backup
   ```

2. **删除旧数据库**：
   ```bash
   rm db/database.db
   ```

3. **执行新迁移**：
   ```bash
   alembic upgrade head
   ```

4. **恢复数据**（如果需要）：
   需要手动将数据从备份恢复到新数据库

## 注意事项

1. **SQLite限制**：
   - SQLite的某些ALTER TABLE操作有限制
   - 某些复杂的变更可能需要重建表

2. **并发问题**：
   - 不要多个进程同时执行迁移
   - 迁移期间不要访问数据库

3. **网络延迟**：
   - 对于MySQL/PostgreSQL，考虑网络延迟
   - 使用事务确保数据一致性

## 相关文档

- [Alembic官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- 项目结构说明（待补充）

## 快速参考

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看历史
alembic history

# 查看SQL（不执行）
alembic upgrade head --sql

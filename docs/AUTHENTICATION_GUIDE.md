# 认证系统使用指南

## 概述

本项目实现了基于内存session的登录和认证系统。所有API接口（除了认证相关的接口）都需要登录后才能访问。

## 功能特性

### 1. Session管理
- **默认过期时间**: 30分钟
- **记住我功能**: 勾选后session过期时间延长至7天
- **自动续期**: 
  - 普通session: 每次访问自动续期（延长30分钟）
  - 记住我session: 每次访问自动续期（延长7天）

### 2. 认证方式
- 支持Cookie认证（推荐）
- 支持Authorization Header认证（Bearer Token）

### 3. 默认账号
- 用户名: `admin`
- 密码: `admin`

### 4. 自定义配置
可以通过`.env`文件自定义账号密码和session配置：

```env
# 管理员账号配置
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_password

# Session配置
SESSION_EXPIRE_MINUTES=30
SESSION_REMEMBER_DAYS=7
```

## API接口

### 1. 登录
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin",
  "remember_me": false
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "username": "admin",
    "session_id": "abc123...",
    "remember_me": false
  }
}
```

登录成功后，服务器会设置`session_id` cookie。

### 2. 登出
```
POST /api/v1/auth/logout
```

**注意**: 需要登录才能访问。

### 3. 获取当前用户信息
```
GET /api/v1/auth/me
```

**响应示例**:
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "username": "admin",
    "logged_in": true
  }
}
```

**注意**: 需要登录才能访问。

### 4. 检查登录状态
```
GET /api/v1/auth/check
```

**响应示例（已登录）**:
```json
{
  "success": true,
  "message": "已登录",
  "data": {
    "username": "admin",
    "logged_in": true
  }
}
```

**响应示例（未登录）**:
```json
{
  "success": true,
  "message": "未登录",
  "data": {
    "username": "",
    "logged_in": false
  }
}
```

**注意**: 此接口不需要登录即可访问。

## 认证方式

### 方式1: Cookie认证（推荐）

登录后，服务器会自动设置`session_id` cookie，后续请求会自动携带该cookie。

### 方式2: Authorization Header

如果无法使用cookie，可以在请求头中添加：

```
Authorization: Bearer <session_id>
```

## 使用示例

### 使用curl

#### 登录
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin","remember_me":false}' \
  -c cookies.txt
```

#### 访问需要认证的接口
```bash
curl http://localhost:8000/api/v1/images \
  -b cookies.txt
```

#### 登出
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -b cookies.txt
```

### 使用JavaScript (fetch)

```javascript
// 登录
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  credentials: 'include', // 重要：允许携带cookie
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin',
    remember_me: false
  })
});

const loginData = await loginResponse.json();
console.log(loginData);

// 访问需要认证的接口
const imagesResponse = await fetch('http://localhost:8000/api/v1/images', {
  method: 'GET',
  credentials: 'include' // 重要：携带cookie
});

const imagesData = await imagesResponse.json();
console.log(imagesData);

// 登出
const logoutResponse = await fetch('http://localhost:8000/api/v1/auth/logout', {
  method: 'POST',
  credentials: 'include'
});
```

### 使用Postman

1. **登录**:
   - Method: POST
   - URL: `http://localhost:8000/api/v1/auth/login`
   - Body: JSON格式
   ```json
   {
     "username": "admin",
     "password": "admin",
     "remember_me": false
   }
   ```

2. **访问受保护的接口**:
   - Postman会自动处理cookie，无需额外配置
   - 或者手动添加Header: `Authorization: Bearer <session_id>`

## 受保护的接口

以下接口需要登录才能访问：

### 存储引擎管理 (`/api/v1/storage/engines/*`)
- `GET /api/v1/storage/engines` - 获取存储引擎列表
- `POST /api/v1/storage/engines` - 创建存储引擎
- `GET /api/v1/storage/engines/{id}` - 获取存储引擎详情
- `PUT /api/v1/storage/engines/{id}` - 更新存储引擎
- `DELETE /api/v1/storage/engines/{id}` - 删除存储引擎
- `POST /api/v1/storage/engines/{id}/test` - 测试存储引擎连接
- `PUT /api/v1/storage/engines/{id}/default` - 设置默认存储引擎
- `GET /api/v1/storage/engines/{id}/usage` - 获取存储使用情况

### 图片管理 (`/api/v1/images/*`)
- `POST /api/v1/images/upload` - 上传图片
- `POST /api/v1/images/upload/batch` - 批量上传图片
- `GET /api/v1/images` - 获取图片列表
- `GET /api/v1/images/{id}` - 获取图片详情
- `DELETE /api/v1/images/{id}` - 删除图片
- `POST /api/v1/images/batch-delete` - 批量删除图片
- `GET /api/v1/images/{id}/info` - 获取图片信息

### 系统配置 (`/api/v1/config/*`)
- `GET /api/v1/config` - 获取所有配置
- `PUT /api/v1/config/batch` - 批量更新配置
- `GET /api/v1/config/{key}` - 获取指定配置
- `PUT /api/v1/config/{key}` - 更新指定配置
- `GET /api/v1/config/settings` - 获取系统设置
- `PUT /api/v1/config/settings` - 更新系统设置
- `DELETE /api/v1/config/{key}` - 删除配置
- `POST /api/v1/config/reload` - 重新加载配置

## 错误处理

### 未登录
```json
{
  "success": false,
  "error_code": "UNAUTHORIZED",
  "message": "未登录，请先登录",
  "data": null
}
```

### Session过期
```json
{
  "success": false,
  "error_code": "UNAUTHORIZED",
  "message": "登录已过期，请重新登录",
  "data": null
}
```

### 用户名或密码错误
```json
{
  "success": false,
  "error_code": "UNAUTHORIZED",
  "message": "用户名或密码错误",
  "data": null
}
```

## 注意事项

1. **Cookie设置**:
   - `httponly`: true (防止XSS攻击)
   - `secure`: 生产环境为true (仅HTTPS传输)
   - `samesite`: lax (防止CSRF攻击)

2. **Session安全**:
   - Session ID使用`secrets.token_urlsafe(32)`生成，具有足够的随机性
   - Session存储在内存中，服务器重启后所有session会失效

3. **生产环境建议**:
   - 修改默认账号密码
   - 启用HTTPS
   - 考虑使用Redis等持久化存储session
   - 设置合理的session过期时间

4. **开发环境**:
   - DEBUG模式下，`secure`为false，允许HTTP传输cookie
   - 可以使用API文档 `/docs` 直接测试接口

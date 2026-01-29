# Cloudflare R2 自定义域名配置指南

## 概述

Cloudflare R2 提供了两种访问方式：
1. **API 端点**：用于上传、下载等操作的 S3 兼容 API 端点
2. **自定义域名**：用于公开访问文件的域名

## URL 生成逻辑

本系统支持以下配置来控制返回的 URL：

### 1. 使用自定义域名（推荐）

当配置了 `custom_domain` 时，所有上传的文件将返回自定义域名的 URL：

**配置示例：**
```json
{
  "type": "s3",
  "name": "Cloudflare R2 存储",
  "config": {
    "endpoint_url": "https://07073f34b877e02232c883dd6e70fe15.r2.cloudflarestorage.com",
    "access_key_id": "your_access_key_id",
    "secret_access_key": "your_secret_access_key",
    "bucket_name": "images",
    "custom_domain": "https://image.notnull.com.cn",
    "use_ssl": true
  },
  "path_rule": "uploads/{date}/{filename}.{ext}",
  "max_capacity": null,
  "is_active": true
}
```

**返回 URL 示例：**
```
https://image.notnull.com.cn/uploads/20260129/image.jpg
```

### 2. 不使用自定义域名

如果没有配置 `custom_domain`，系统将使用 R2 的 API 端点生成 URL：

**配置示例：**
```json
{
  "type": "s3",
  "name": "Cloudflare R2 存储",
  "config": {
    "endpoint_url": "https://07073f34b877e02232c883dd6e70fe15.r2.cloudflarestorage.com",
    "access_key_id": "your_access_key_id",
    "secret_access_key": "your_secret_access_key",
    "bucket_name": "images",
    "use_ssl": true
  },
  "path_rule": "uploads/{date}/{filename}.{ext}",
  "max_capacity": null,
  "is_active": true
}
```

**返回 URL 示例：**
```
https://07073f34b877e02232c883dd6e70fe15.r2.cloudflarestorage.com/images/uploads/20260129/image.jpg
```

## 配置参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `endpoint_url` | 是 | R2 API 端点，用于上传、下载等操作 |
| `access_key_id` | 是 | R2 访问密钥 ID |
| `secret_access_key` | 是 | R2 访问密钥 |
| `bucket_name` | 是 | R2 存储桶名称 |
| `custom_domain` | 否 | 自定义域名，用于生成公开访问 URL |
| `base_path` | 否 | 文件存储路径前缀，默认为空 |
| `use_ssl` | 否 | 是否使用 SSL，默认为 true |

## 如何获取 R2 配置信息

### 1. 获取 API 端点

1. 登录 Cloudflare Dashboard
2. 进入 R2 服务
3. 选择你的存储桶
4. 查看 "Settings" → "R2 API" → "S3 API Endpoint"

### 2. 获取访问密钥

1. 在 R2 Dashboard 中，进入 "Manage R2 API Tokens"
2. 创建新的 API Token，或查看现有的 Token
3. 保存 `Access Key ID` 和 `Secret Access Key`

### 3. 配置自定义域名

1. 在 R2 存储桶设置中，进入 "Custom Domains"
2. 添加你的自定义域名（如 `image.notnull.com.cn`）
3. 按照提示配置 DNS 记录
4. 等待 SSL 证书生成完成

## 优先级说明

URL 生成的优先级如下：

1. **最高优先级**：`custom_domain`（如果配置）
2. **次优先级**：使用 `endpoint_url` 生成 URL（R2 格式）
3. **默认**：AWS S3 标准格式

## 注意事项

1. `custom_domain` 必须在 Cloudflare R2 中正确配置并指向该存储桶
2. 确保 DNS 记录正确解析，并且 SSL 证书已生成
3. 如果使用自定义域名，确保域名包含协议（`https://` 或 `http://`）
4. 系统支持向后兼容旧的 `cdn_domain` 配置项

## 测试配置

配置完成后，可以通过以下方式测试：

```bash
# 上传一张图片测试
curl -X POST http://localhost:8000/api/v1/images/upload \
  -H "Authorization: Bearer your_token" \
  -F "file=@test.jpg"

# 检查返回的 URL 是否正确
```

## 常见问题

### Q: 为什么返回的 URL 不是自定义域名？

A: 检查以下几点：
1. 确认配置中正确设置了 `custom_domain` 参数
2. 确认自定义域名包含协议前缀（如 `https://`）
3. 检查存储引擎是否已激活并设为默认

### Q: 自定义域名无法访问？

A: 检查以下几点：
1. 确认自定义域名已在 Cloudflare R2 中正确配置
2. 确认 DNS 记录正确解析
3. 确认 SSL 证书已生成
4. 检查存储桶的公开访问设置

### Q: 如何从旧配置迁移？

A: 如果之前使用的是 `cdn_domain`，系统会自动兼容。建议在更新配置时使用新的 `custom_domain` 参数名称。

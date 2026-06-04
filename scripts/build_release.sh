#!/bin/bash
# scripts/build_release.sh
# 运行环境: macOS/Linux
# 用途: 打包项目源码为 ZIP 压缩包以便上传至 Windows 服务器

VERSION=$(grep "APP_VERSION=" .env | cut -d'=' -f2)
[ -z "$VERSION" ] && VERSION="v1.1.1"
OUTPUT="frank_gemini_${VERSION}.zip"

echo "📦 开始打包版本: ${VERSION}..."

# 确保 scripts 目录存在
mkdir -p scripts

# 使用 zip 打包，排除无关文件
# 注意：包含所有必要的 Dockerfile 和配置文件
zip -r "${OUTPUT}" . \
    -x "*.DS_Store*" \
    -x "*__pycache__*" \
    -x "*.git*" \
    -x "logs/*" \
    -x ".agent-artifacts/*" \
    -x "data/*.db-journal" \
    -x "${OUTPUT}"

echo "------------------------------------------"
echo "✅ 打包完成: ${OUTPUT}"
echo "👉 部署指引:"
echo "1. 将此 ZIP 文件上传至 Windows 服务器。"
echo "2. 解压后，右键管理员权限运行 PowerShell。"
echo "3. 执行: .\\scripts\\deploy_win.ps1"
echo "------------------------------------------"

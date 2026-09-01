# GitHub Pages 部署指南

将代理节点链接生成器部署到 GitHub Pages，任何人在浏览器中打开即可使用，无需安装 Python。

---

## 方案原理

```
GitHub Actions（服务端）              用户浏览器
┌─────────────────────┐          ┌──────────────────────┐
│  每天自动运行 Python  │          │  打开 GitHub Pages    │
│  → 生成 HTML + TXT   │  ──→     │  → 直接查看嵌入数据   │
│  → 部署到 Pages       │          │  → 无需 CORS 请求     │
└─────────────────────┘          └──────────────────────┘
```

**为什么不用浏览器直接 fetch？**
GitLab 的 raw 文件不支持 CORS（`Access-Control-Allow-Origin`），浏览器会阻止跨域请求。
解决方案：在 GitHub Actions 服务端运行 Python 脚本生成 HTML，数据直接嵌入页面，用户打开即可查看。

---

## 部署步骤（5 分钟）

### 步骤 1：创建 GitHub 仓库

1. 登录 [github.com](https://github.com)
2. 点击 **"+"** → **"New repository"**
3. 仓库名：`proxy-links`（或你喜欢的名字）
4. 选择 **Public**
5. ✅ 勾选 **"Add a README file"**
6. 点击 **"Create repository"**

### 步骤 2：上传文件

**方式 A：网页上传（最简单）**

将以下文件上传到仓库**根目录**：
- `Get_links.py`（项目根目录的 Python 脚本）
- `.github/workflows/deploy.yml`（在 `web/.github/workflows/` 中）

**方式 B：Git 命令行**

```bash
git clone https://github.com/你的用户名/proxy-links.git
cd proxy-links

# 复制文件
cp /path/to/Get_links.py ./
mkdir -p .github/workflows
cp /path/to/web/.github/workflows/deploy.yml .github/workflows/

# 提交并推送
git add .
git commit -m "添加代理节点链接生成器"
git push origin main
```

### 步骤 3：启用 GitHub Pages（使用 Actions 作为源）

1. 进入仓库 → **Settings** → 左侧 **Pages**
2. **Source** 部分选择 **"GitHub Actions"**（不是 Branch！）
3. 保存

### 步骤 4：等待首次构建

1. 进入仓库 → **Actions** 标签页
2. 点击 **"Build and Deploy to GitHub Pages"** 工作流
3. 等待绿色 ✅（通常 2-3 分钟）
4. 完成后页面顶部出现链接：
   ```
   ✅ Your site is live at https://你的用户名.github.io/proxy-links/
   ```

### 步骤 5：验证

打开浏览器访问：
```
https://你的用户名.github.io/proxy-links/
```

你应该看到所有节点链接，数据已嵌入页面，无需任何网络请求。

---

## 自动更新

工作流已配置为每天北京时间 **23:00** 自动运行，从远程服务器拉取最新配置并更新页面。

也可以手动触发：
1. 进入 **Actions** → **"Build and Deploy to GitHub Pages"**
2. 点击 **"Run workflow"** → **"Run workflow"**

---

## 文件说明

| 文件 | 位置 | 说明 |
|------|------|------|
| `Get_links.py` | 仓库根目录 | Python 脚本（服务端运行） |
| `.github/workflows/deploy.yml` | 仓库中 | GitHub Actions 工作流 |
| 生成的 `index.html` | 自动部署 | 包含所有节点数据的 HTML 页面 |
| 生成的 `proxy_links.txt` | 通过 Actions artifact 下载 | 纯链接订阅文件 |

---

## 常见问题

### Q: 页面打开是空白的？

**A:** 检查 Actions 是否成功运行。进入 Actions 标签页查看最近的构建是否为绿色 ✅。

### Q: Actions 运行失败？

**A:** 常见原因：
- GitLab 临时不可用 → 手动重新运行 workflow
- Python 脚本语法错误 → 检查 `Get_links.py` 是否完整上传

### Q: 如何下载 proxy_links.txt？

**A:** 
1. 进入 **Actions** → 最近的成功构建
2. 展开 **"Build"** job
3. 点击底部 **"Artifacts"** 部分的 **"site"** 下载
4. 解压后包含 `proxy_links.txt`

### Q: 可以私有仓库吗？

**A:** 可以！GitHub Pages 对私有仓库也可用（需要 GitHub Pro 或组织账户）。

### Q: 如何自定义域名？

**A:**
1. DNS 添加 CNAME 记录指向 `你的用户名.github.io`
2. 仓库 Settings → Pages → Custom domain 填入域名
3. 勾选 "Enforce HTTPS"

---

## 本地预览

如果只想本地查看生成效果，不需要 GitHub Actions：

```bash
# 运行 Python 脚本生成 HTML
python Get_links.py

# 浏览器打开生成的 HTML 文件
# Windows: start proxy_links.html
# macOS:   open proxy_links.html
# Linux:   xdg-open proxy_links.html
```

---

## 替代方案：Docker 部署

如果需要更频繁的更新或私有网络环境，可参考 `docker/README.md` 使用 Docker 方案。

# ZenClean (禅清) Web 端 SEO 全面优化方案

本方案针对 ZenClean 推广网页 (`index.html`)，旨在通过技术手段、内容布局和搜索引擎规则，提升网站在百度、Google、Bing 等搜索引擎中的自然排名和曝光量。

## 一、 核心长尾关键词策略 (Long-Tail Keywords)

这些词是用户在遇到问题时最常搜索的，转化率最高。需要在页面内容（如 FAQ 或底部说明）中自然融入：

1. **痛点场景词**
   - "C盘满了/爆红怎么清理？"
   - "Win10/Win11 C盘越来越小怎么办？"
   - "C盘哪些文件可以安全删除"
   - "AppData文件夹太大了怎么清理"
2. **功能指代词**
   - "C盘软件无损转移到D盘工具"
   - "Windows 应用程序搬家软件"
   - "防误删的电脑清理软件"
   - "AI智能系统垃圾清理"
3. **效用与竞品词**
   - "一键释放几十G的C盘空间"
   - "老电脑提速优化神器"
   - "比 360/火绒 更纯净的清理工具"

## 二、 页面内 SEO (On-Page SEO)

### 1. 结构化数据 (Schema.org / JSON-LD)
向搜索引擎明确声明这是一个软件产品，有助于在搜索结果中展示“富文本摘要”（如产品类别、免费等信息）。
**执行方案**：在 `<head>` 标签中添加 JSON-LD 脚本：
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "ZenClean 禅清",
  "operatingSystem": "Windows 10, Windows 11",
  "applicationCategory": "UtilitiesApplication",
  "description": "融合 AI 智能分诊与极客底层爆破的 Windows C 盘清理工具，支持应用无损搬家与时光机恢复。",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "CNY"
  }
}
</script>
```

### 2. 标准化链接 (Canonical Tag)
防止搜索引擎因不同的 URL（如带 www 和不带 www，或带 trailing slash）导致权重分散。
**执行方案**：在 `<head>` 中添加规范链接（上线时需替换为实际上线的域名）：
`<link rel="canonical" href="https://你的正式域名.com/" />`

### 3. Open Graph (OG) 标签修复
目前的 `og:image` 使用了相对路径 `assets/hero_bg.png`，在社交软件（如微信、TG）分享时可能无法抓取到图片。
**执行方案**：改为绝对路径，例如 `https://你的正式域名.com/assets/hero_bg.png`。

### 4. 标题层级 (Heading Tags)
确保页面具有良好的语义结构，只有一个 `<h1>`。
**执行方案**：目前 `<h1>` 是 "定义清理的新高度"，表现良好。后续添加内容时，保证主模块使用 `<h2>`，子模块使用 `<h3>`，不出现断层。

## 三、 面向流量转化：新增 FAQ 问答模块

在页面底部或下载区域上方，增加一个“常见问题”模块。这能完美地、自然地容纳长尾关键词。
**文案示例**：
- **问：C盘爆红满了怎么清理？哪些文件可以安全删除？**
  答：ZenClean 搭载云端 AI 大模型，智能研判 C 盘冗余文件，精准区分系统核心与无用缓存，确保安全删除不误删，轻松释放几十G空间。
- **问：安装在 C 盘的软件可以无损转移到 D 盘吗？**
  答：可以。ZenClean 的“系统搬家”功能采用底层 NTFS 目录映射技术，一键将大型软件和游戏资产迁移至其他盘符，实现真正的无损搬家。

## 四、 页面加载与体验优化 (Core Web Vitals)

1. **图片懒加载**：对于非首屏图片（如底部的功能截图、火绒查杀截图），增加 `loading="lazy"` 属性。
2. **图片格式**：将大量 `.png` 转换为 `.webp` 格式，大幅减少加载体积，提升移动端秒开率。
3. **资源压缩**：上线前压缩 `styles.css` 和 `script.js`。

## 五、 站点收录 (Index & Crawl)

网站部署上线后，必须执行以下操作以加速收录：
1. **生成 sitemap.xml**：列出网站的所有有效页面。
2. **配置 robots.txt**：允许各大搜索引擎蜘蛛抓取。
3. **主动提交**：将网站提交到**百度搜索资源平台**和 **Google Search Console**。

# Personal Learning Site

这是一个本地优先的个人学习网站。首页负责整体导览，知识学习总览下分为三个方向：

- 编程相关知识
- 编程相关项目
- 科研类内容

分类页使用统一的二级导航入口排列具体条目。当前已有的 `hstring` 页面位于“编程相关项目”下，用来验证“用图形解释代码运行模型”的方式。

## 本地预览

先安装生成器依赖并构建静态产物：

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python -m generator build

然后预览 `dist/`：

    python3 -m http.server 8000 --directory dist

打开 http://localhost:8000/。`python -m generator check` 会重建产物，并检查 front matter、HTML 基本结构、本地链接和资源引用。

## 目录约定

- `content/`：Markdown 内容和 front matter，是正文事实源。
- `templates/`：页面布局和可复用模板。
- `generator/`：Python 静态生成器与检查逻辑。
- `assets/`：共享 CSS、JavaScript 和媒体资源。
- `dist/`：生成后用于预览或发布的静态文件，不作为编辑入口。

当前第一条生成内容是 `projects/hstring/`；首页和分类页仍复制旧手写页面作为迁移对照。HString 页面中的内存图和执行轨迹暂时以受控 HTML 保存在 Markdown 中。

源码事实源是 GitHub 上的 hstring 仓库，本示例固定到提交 015d0bdcd7d6659400883a099f8ba568d751623e。网站只记录和解释这个历史快照，不继续开发或修改旁边的源码仓库。

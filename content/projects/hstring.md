---
kind: project
status: completed
title: "hstring · 手写字符串类"
slug: hstring
summary: "把一个自定义字符串类拆成对象、缓冲区、数据移动和边界行为。这个页面记录历史实现，不代表生产可用性，也不安排继续开发。"
updated: "2026-09-21"
order: 1
tags:
  - C++
  - memory
card_kicker: "C++ / MEMORY · CLOSED PROJECT"
card_script: "hello"
source: "https://github.com/tangren02/hstring/tree/015d0bdcd7d6659400883a099f8ba568d751623e"
---

<!--
  The first migration keeps the verified HString diagrams as controlled HTML.
  They remain Markdown content and will be extracted into reusable components
  only when a second project needs the same visual language.
-->
<section class="project-hero">
<div class="breadcrumb"><a href="../../">首页</a><span>/</span><span>编程相关项目</span><span>/</span><span>已结束项目</span></div>
<div class="eyebrow"><span class="status-dot"></span> CLOSED PROJECT / SOURCE SNAPSHOT</div>
<h1><span>hstring</span><br />手写字符串类</h1>
<p class="lede">把一个自定义字符串类拆成对象、缓冲区、数据移动和边界行为。这个页面记录历史实现，不代表生产可用性，也不安排继续开发。</p>
<div class="project-meta"><span class="status-pill">已结束 · 暂无继续开发计划</span><span class="meta-separator">·</span><a href="https://github.com/tangren02/hstring/tree/015d0bdcd7d6659400883a099f8ba568d751623e" target="_blank" rel="noreferrer">GitHub @ 015d0bd <span>↗</span></a></div>
</section>

<section class="callout-grid">
<article class="callout objective"><span class="callout-icon">◎</span><div><span class="kicker">LEARNING GOAL</span><h2>我要看懂什么？</h2><p>一个 <code>hstring</code> 对象如何拥有一块字符缓冲区；构造、拷贝、拼接、查找、删除和替换怎样改变它。</p></div></article>
<article class="callout boundary"><span class="callout-icon">!</span><div><span class="kicker">SCOPE BOUNDARY</span><h2>这页不证明什么？</h2><p>不证明零拷贝、引用计数、性能提升或生产可用性。没有基准数据的句子只保留为设计目标。</p></div></article>
</section>

<section class="section project-section">
<div class="section-heading"><div><span class="kicker">01 / MODEL</span><h2>先把对象画出来</h2></div><p>类本身很小，真正需要追踪的是指针指向的字符缓冲区，以及长度和容量两个数字。</p></div>
<div class="model-stage">
<div class="object-card"><div class="object-title"><span class="object-icon">h</span><div><strong>hstring</strong><small>对象本体</small></div></div><div class="field"><span>buffer</span><b>─────────▶</b><i>char*</i></div><div class="field"><span>buffer_size</span><b>128</b><i>capacity</i></div><div class="field"><span>data_length</span><b>5</b><i>used chars</i></div></div>
<div class="connector"><span>owns</span><b>↘</b></div>
<div class="buffer-card"><div class="buffer-head"><span>heap buffer</span><span class="capacity">128 bytes</span></div><div class="cells" aria-label="字符缓冲区示意"><span class="used">h</span><span class="used">e</span><span class="used">l</span><span class="used">l</span><span class="used">o</span><span class="null-cell">\0</span><span></span><span></span><span></span><span></span><span></span><span class="ellipsis">···</span></div><div class="buffer-foot"><span><em class="legend used-legend"></em>已使用</span><span><em class="legend null-legend"></em>结束符</span><span><em class="legend free-legend"></em>剩余容量</span></div></div>
</div>
<div class="insight"><span class="insight-line"></span><p><strong>观察：</strong>容量是分配出来的空间，长度是当前字符串的有效字符数。<code>\0</code> 不计入 <code>data_length</code>，但它决定了 C 风格字符串在哪里结束。</p></div>
</section>

<section class="section project-section">
<div class="section-heading"><div><span class="kicker">02 / DESIGN VS CODE</span><h2>设计目标和代码事实</h2></div><p>原始说明是一份历史设计目标；以下内容以 GitHub 快照中的 <code>hstring.hpp/.cpp</code> 为事实基线。</p></div>
<div class="compare-grid">
<article class="compare-card"><span class="compare-label target">DESIGN TARGET</span><h3>减少频繁分配</h3><p>通过固定初始缓冲区和倍增容量，避免每次字符变化都申请新空间。</p><span class="compare-state">部分实现</span></article>
<article class="compare-card"><span class="compare-label fact">CODE FACT</span><h3>对象和结果各自拥有缓冲区</h3><p>构造函数、拷贝构造和两个 <code>operator+</code> 都会创建字符数组；当前没有共享缓冲区或引用计数。</p><span class="compare-state warning">与目标有差异</span></article>
<article class="compare-card"><span class="compare-label target">DESIGN TARGET</span><h3>零拷贝 / 引用计数</h3><p>历史说明把它写成核心奥义，并宣称性能收益。</p><span class="compare-state warning">没有代码或基准证据</span></article>
<article class="compare-card"><span class="compare-label fact">CODE FACT</span><h3>显式复制和移动</h3><p><code>memcpy</code> 负责复制，<code>memmove</code> 负责删除或替换时的重叠区域移动。</p><span class="compare-state">可从源码追踪</span></article>
</div>
</section>

<section class="section project-section">
<div class="section-heading"><div><span class="kicker">03 / TRACE</span><h2>沿一条路径走完</h2></div><p>先看状态变化，再回到函数。每一块都对应一个可以在源码中定位的动作。</p></div>
<div class="trace">
<article class="trace-step"><div class="step-index">01</div><div class="step-body"><div class="step-head"><h3>构造对象</h3><code>hstring s("hello")</code></div><p>计算输入长度，分配初始容量 128，并复制 <code>hello\0</code>。</p><div class="trace-buffer"><span>h</span><span>e</span><span>l</span><span>l</span><span>o</span><span class="null-cell">\0</span><span class="ghost"></span><span class="ghost"></span><span class="ghost"></span><span class="ghost"></span></div><div class="trace-note"><span>data_length = 5</span><span>buffer_size = 128</span></div></div></article>
<article class="trace-step"><div class="step-index">02</div><div class="step-body"><div class="step-head"><h3>查找子串</h3><code>s.find("ll") → 2</code></div><p>从左到右比较字符，第一次完整匹配的位置是 2；当前实现使用暴力匹配。</p><div class="scan-line"><span>h</span><span>e</span><span class="scan-hit">l</span><span class="scan-hit">l</span><span>o</span><span class="null-cell">\0</span><b>↑ 2</b></div></div></article>
<article class="trace-step"><div class="step-index">03</div><div class="step-body"><div class="step-head"><h3>删除子串</h3><code>s - "ll"</code></div><p>先复制出结果对象，再从首次出现的位置开始用 <code>memmove</code> 覆盖剩余内容。</p><div class="before-after"><div><small>before</small><span>h e <mark>l l</mark> o \0</span></div><b>memmove →</b><div><small>after</small><span>h e o \0</span></div></div></div></article>
<article class="trace-step"><div class="step-index">04</div><div class="step-body"><div class="step-head"><h3>替换并判断扩容</h3><code>s.replace(2, "ll", "XXXX")</code></div><p>新字符串变长时申请更大的缓冲区，复制前段、替换段和剩余段；容量足够时则原地移动。</p><div class="branch"><div><span class="branch-dot cyan"></span><strong>容量足够</strong><small>memmove + memcpy</small></div><div><span class="branch-dot orange"></span><strong>容量不足</strong><small>new[] + 三段复制</small></div></div></div></article>
</div>
</section>

<section class="section project-section defects-section">
<div class="section-heading"><div><span class="kicker">04 / OPEN DEFECTS</span><h2>当前实现的未完成缺陷</h2></div><p>这些标记描述快照中的真实问题；HString 已结束，页面不把它们转成新的开发任务。</p></div>
<div class="defect-list">
<article class="defect"><span class="severity high">D1</span><div><h3>设计文档宣称了代码没有的机制</h3><p>说明文档提到引用计数、零拷贝和“性能降低 60% 以上”，但 <code>hstring.hpp/.cpp</code> 没有对应实现或基准数据。</p><a class="source-ref" href="https://github.com/tangren02/hstring/blob/015d0bdcd7d6659400883a099f8ba568d751623e/hstring字符实现要求.md#L22-L28" target="_blank" rel="noreferrer">hstring字符实现要求.md · 第二章 ↗</a></div><span class="defect-kind">事实边界</span></article>
<article class="defect"><span class="severity high">D2</span><div><h3><code>size_t</code> 返回值使用 <code>-1</code></h3><p><code>find</code> 的失败值会转换成无符号大整数；<code>operator-</code> 再把它转成 <code>int</code>，失败语义不稳定。</p><a class="source-ref" href="https://github.com/tangren02/hstring/blob/015d0bdcd7d6659400883a099f8ba568d751623e/hstring.cpp#L216-L246" target="_blank" rel="noreferrer">hstring.cpp · find / operator- ↗</a></div><span class="defect-kind">类型契约</span></article>
<article class="defect"><span class="severity medium">D3</span><div><h3><code>pos &lt; 0</code> 永远不会成立</h3><p><code>replace</code> 的 <code>pos</code> 是 <code>size_t</code>，负数检查无效；越界只能依赖后面的无符号范围判断。</p><a class="source-ref" href="https://github.com/tangren02/hstring/blob/015d0bdcd7d6659400883a099f8ba568d751623e/hstring.cpp#L330-L357" target="_blank" rel="noreferrer">hstring.cpp · replace ↗</a></div><span class="defect-kind">边界检查</span></article>
<article class="defect"><span class="severity medium">D4</span><div><h3><code>operator+</code> 没有做到目标中的按需分配</h3><p>两个拼接重载都会为结果对象直接 <code>new char[...]</code>，即使结果很短也不会复用既有容量。</p><a class="source-ref" href="https://github.com/tangren02/hstring/blob/015d0bdcd7d6659400883a099f8ba568d751623e/hstring.cpp#L69-L121" target="_blank" rel="noreferrer">hstring.cpp · operator+ ↗</a></div><span class="defect-kind">设计差异</span></article>
<article class="defect"><span class="severity low">D5</span><div><h3>查找位置从 <code>size_t</code> 窄化到 <code>int</code></h3><p>长字符串的索引可能超出 <code>int</code> 的可表示范围，<code>operator-</code> 的位置变量应与查找接口保持一致。</p><a class="source-ref" href="https://github.com/tangren02/hstring/blob/015d0bdcd7d6659400883a099f8ba568d751623e/hstring.cpp#L223-L236" target="_blank" rel="noreferrer">hstring.cpp · operator- ↗</a></div><span class="defect-kind">可扩展性</span></article>
</div>
</section>

<section class="section project-section evidence-section">
<div class="section-heading"><div><span class="kicker">05 / EVIDENCE</span><h2>我实际看到了什么</h2></div><p>运行现有快照中的 <code>main</code>，得到下面这些结果。它们验证行为，不验证性能承诺。</p></div>
<div class="evidence-grid"><div class="terminal"><div class="terminal-bar"><span></span><span></span><span></span><b>hstring / main</b></div><pre><code>$ ./main
find "def" = 3
12XXXX56789
12X789
2147483647
aaabbbccc</code></pre></div><div class="evidence-copy"><div class="evidence-item"><span>✓</span><div><strong>可复现行为</strong><p>查找、替换、整数赋值、拷贝构造和连续拼接都有现成示例。</p></div></div><div class="evidence-item muted-item"><span>×</span><div><strong>尚无性能证据</strong><p>没有基准脚本或对照数据，因此页面不写性能结论。</p></div></div><a class="source-link" href="https://github.com/tangren02/hstring/tree/015d0bdcd7d6659400883a099f8ba568d751623e" target="_blank" rel="noreferrer">查看 GitHub 源码快照 <span>↗</span></a></div></div>
</section>

<section class="section reflection"><div class="reflection-mark">✦</div><div><span class="kicker">TAKEAWAY</span><h2>这个项目留下的学习价值</h2><p>它不是一个需要继续包装的“高性能字符串”，而是一张很好的 C++ 内存管理练习图：对象拥有什么、什么时候复制、什么时候扩容、边界条件在哪里，以及设计文档为什么必须和代码对齐。</p></div></section>

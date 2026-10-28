# 配套工具边界

## 可用工具

- `assets/template.html`：自包含起手模板，默认模式B八节骨架；A按需换成方案章节，并统一移除 `rep`。
- `assets/blocks.html`：同一套CSS的后台壳/对照/矩阵/ASCII/Mermaid源码卡/风险卡，示范不是实际业务证据。
- `assets/render-mermaid.py`：Python3标准库编排**已有**mmdc；每份文件全部卡成功后才原子替换，失败非零且本文件不变；多文件不是跨文件事务。三遍不改内容应一致。
- `assets/check-overflow.py`：Python3标准库编排已有Node >=22 + Chrome/Chromium。
- `assets/probe-browser.mjs`：Node内置WebSocket接Chrome CDP，临时独立profile，浏览器退出后清理；不复用用户登录资料。

## 浏览器测什么

CDP `Emulation.setDeviceMetricsOverride`设置CSS布局视口，独立报告 `innerWidth` / `clientWidth`。
允许垂直滚动条令clientWidth略小；innerWidth必须严格等于请求宽度。
检查文档横向宽度及未被局部滚动容器兜住的元素；宽表/ASCII/宽SVG只在自己的容器横滚是合法设计。
检查不是完整无障碍/截图像素比/业务验收，也不保证图内文字没有裁切；必须人工看真实截图。

`--screenshots=<dir>`只在明确指定时写PNG，不上传；文件名带归档路径hash，避免多个index.html互相覆盖。
首次执行建议对模板运行，再对最终报告运行。最终内容修改后旧证据失效。

```bash
python3 -m unittest discover -s tests -p 'html_mockup*_test.py'
python3 <skill-dir>/assets/check-overflow.py <page> --widths=390,768,1440
```

第二条默认不禁用Chrome沙箱。可信隔离容器确实不能启动时才显式传`--no-sandbox`，证据中注明。
实际检查不依赖静态服务器，CDP只绑定127.0.0.1临时端口；不是公网发布服务。
仅检查自己生成的静态本地页；不要用它打开带真实登录数据/第三方不可信脚本的页面。
Node版本不足、Chrome/mmdc缺失、文件不存在、输出缺失、探测异常、宽度不符，都按未验证非零处理。
退出码：0=本次请求全部通过；1=测量失败/溢出或渲染失败；2=输入/运行前提缺失（个别文件缺失在逐文件处理中为1）。

## Mermaid限制

仅识别指定`figure[data-mermaid]`卡，源码必须HTML转义；不支持旧版任意嵌套`.mmd`结构，发现后明确失败。
SVG必须有viewBox；不接受外链资源、脚本、事件或foreignObject，渲染配置关闭flowchart HTML labels。
复杂图型若输出嵌入HTML会明确失败，可在本地核对后改成受控原生SVG；不能绕过后说图已验收。
已有图保留折叠源码；修改源码后需`--force`；默认重复执行不重渲，保留用户CSS。
渲染需要Chrome时可用CHROME_PATH指定；mmdc本身可有其他依赖，但本工具不会自动下载或修复它。

## 刻意不附带

不含bootstrap、serve、自动依赖安装、HTTP公网/端口分享、机器域名推导、批量改字号工具或生产发布脚本。
不强加issue系统、特定前端框架、数据库或固定分支；不在当前机器安装任何技能。

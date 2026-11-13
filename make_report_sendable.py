# -*- coding: utf-8 -*-
"""
make_report_sendable.py —— 把 Allure 单文件报告变成「双击就能看」的版本
=============================================================================
背景：allure generate --single-file 产出的 index.html 把应用脚本写成了
    <script src="data:text/javascript;...;base64,...">
这种 data:URI 写法在 file://（双击打开）下不被浏览器执行，页面永远转圈。
本脚本把它解码成真正的内联 <script>，处理后单文件即可直接双击查看、直接发人。

用法（项目根目录执行）：
    .venv\\Scripts\\python.exe make_report_sendable.py <单文件报告目录>
例如：
    .venv\\Scripts\\python.exe make_report_sendable.py allure-report-single
效果：目录下生成 index_sendable.html（与原 index.html 并存，不覆盖）

完整流程（发给别人看的报告）：
    1) allure generate --single-file --lang zh --name "报告名" --clean -o allure-report-single allure-results
    2) .venv\\Scripts\\python.exe make_report_sendable.py allure-report-single
    3) 把 allure-report-single\\index_sendable.html 发出去（可改名），对方双击即看
"""
import base64
import re
import sys
from pathlib import Path


def make_sendable(report_dir: Path) -> Path:
    src = report_dir / "index.html"
    html = src.read_text(encoding="utf-8")

    pat = re.compile(r'<script src="data:text/javascript;[^"]*base64,([^"]+)"></script>')
    matches = pat.findall(html)
    print(f"发现 data:URI 脚本数: {len(matches)}")
    if not matches:
        print("没有需要处理的脚本（可能已是可双击版本），原样返回。")
        return src

    def repl(m):
        js = base64.b64decode(m.group(1)).decode("utf-8")
        # 内联脚本里若含 </script> 会提前闭合标签，统一转义为 <\/script>
        n = js.lower().count("</script")
        print(f"  内联大小: {len(js)} 字节 | 含 </script 次数: {n}")
        js = re.sub(r"</(script)", r"<\\/\1", js, flags=re.I)
        return "<script>" + js + "</script>"

    html, replaced = pat.subn(repl, html)
    print(f"替换数: {replaced}")

    out = report_dir / "index_sendable.html"
    out.write_text(html, encoding="utf-8")
    print(f"已生成: {out}（{out.stat().st_size} 字节），把这一个文件发出去即可。")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python make_report_sendable.py <单文件报告目录>")
    make_sendable(Path(sys.argv[1]))

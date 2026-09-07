# 申请模板与填写示例

下载目录由 `app/api/routes/templates.py` 的白名单管理，新增文件必须登记。原有四份表格保持不变；文件类型的 `aliases` 将签章扫描件映射到对应原表，下载提示会说明必须自行填写、真实签章后扫描。

新示例均为虚构参考，不是正式审批文件，不含签名或印章：

- `meiyu_application_example.docx`：普通场地初审的信息填写参考。
- `yueyuan_plan_example.docx`：悦园三楼策划书内容参考。
- `supporting_material_example.docx`：证明/补充说明参考。
- `key_borrow_example.docx` 与 `.pdf`：可编辑借用参考与 PDF 阅读示例，借用接口只接受 PDF。

再生成：使用带 `python-docx`、`reportlab` 的 Python 运行 `scripts/generate_material_examples.py`。默认 PDF 字体来自 macOS 的 Arial Unicode，可用 `MEIYU_EXAMPLE_FONT` 指定另一个包含中文、允许嵌入的 TTF 字体路径。再生成后须检查 DOCX/PDF 的中文、换页和溢出，不要覆盖原有表格。

前端在 `materialLibrary.ts` 统一按申请类型、材料用途和别名匹配下载；未知用途明确提示未提供，不回退到不相关文件。新增必交材料时同步维护别名，并运行 `python -m unittest discover -s tests -v`。

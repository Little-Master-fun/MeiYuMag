# 申请模板与填写示例

下载目录由 `app/api/routes/templates.py` 的白名单管理，新增文件必须登记。原有四份表格保持不变；文件类型的 `aliases` 将签章扫描件映射到对应原表，下载提示会说明必须自行填写、真实签章后扫描。

示例仅供参考，不是正式审批文件，不能原样提交：

- `meiyu_application_example.docx`：用户提供的《山东大学美育文化馆活动申请表2026.6.5.docx》，原字节保留；用户已确认保留其中的个人信息，不由生成脚本覆盖。
- `yueyuan_plan_example.docx`：悦园三楼策划书内容参考。
- `supporting_material_example.docx`：证明/补充说明参考。
- `key_borrow_example.png`：用户提供的钥匙借用图片示例，唯一展示的钥匙参考文件。旧 DOCX/PDF 保留在源文件历史中，但不再出现在下载白名单，也不再生成。
- 钥匙借用接口仍只接受 PDF。纸质材料需扫描并开启 OCR，导出含文字层的可搜索 PDF；当前后端没有图片 OCR，不能识别纯图片扫描 PDF。

再生成：使用带 `python-docx` 的 Python 运行 `scripts/generate_material_examples.py`，仅更新悦园策划书与补充说明示例，跳过用户提供的原文件。生成后须检查中文、换页和溢出，不要覆盖原有表格。

前端在 `materialLibrary.ts` 统一按申请类型、材料用途和别名匹配下载；未知用途明确提示未提供，不回退到不相关文件。新增必交材料时同步维护别名，并运行 `python -m unittest discover -s tests -v`。

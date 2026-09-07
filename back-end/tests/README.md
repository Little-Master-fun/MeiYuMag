# 申请工作流回归测试

在后端环境安装 `pip install -r requirements-test.txt`，运行：

```sh
python -m unittest discover -s tests -v
```

测试使用临时 SQLite 数据库和临时上传目录，通过 HTTP 调用 FastAPI。
AI 和通知服务被替换为测试响应，不访问实际业务数据库、不调用外部 AI、不发送邮件。
覆盖初审驳回及重提、签章清单、按类型批量补交与文件版本、审批状态约束、取消释放预约、下载权限、文件校验和场地日期冲突。

前端提交规则与 multipart 字段回归：在 `front-end` 中使用 Node 22.18+ 或 Node 24 执行 `npm test`。

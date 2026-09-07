"""Public reference downloads only; no database, AI or email is touched."""
import unittest
from io import BytesIO
from zipfile import ZipFile

import httpx
from pypdf import PdfReader

from app.main import create_app
from app.services.application_workflow import signed_file_types


class TemplateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_catalog_downloads_exist_and_have_correct_formats(self):
        response = await self.client.get("/api/v1/templates")
        self.assertEqual(response.status_code, 200)
        catalog = response.json()
        self.assertEqual(len(catalog), 9)
        for item in catalog:
            download = await self.client.get(item["download_url"])
            self.assertEqual(download.status_code, 200, item["name"])
            self.assertIn("attachment", download.headers["content-disposition"])
            if item["name"].endswith(".pdf"):
                self.assertEqual(download.headers["content-type"], "application/pdf")
                reader = PdfReader(BytesIO(download.content))
                self.assertEqual(len(reader.pages), 1)
                self.assertIn("虚构", reader.pages[0].extract_text())
            else:
                self.assertIn("wordprocessingml", download.headers["content-type"])
                with ZipFile(BytesIO(download.content)) as doc:
                    self.assertIn("word/document.xml", doc.namelist())
                    if item["kind"] == "example":
                        self.assertIn("请勿原样提交", doc.read("word/document.xml").decode())

    async def test_every_signed_requirement_has_a_corresponding_source(self):
        catalog = (await self.client.get("/api/v1/templates")).json()
        for application_type in ["meiyu_venue", "yueyuan_third_floor"]:
            for file_type in signed_file_types(application_type):
                self.assertTrue(any(
                    item["application_type"] == application_type and
                    (item["file_type"] == file_type or file_type in item["aliases"])
                    for item in catalog
                ), file_type)

    async def test_unknown_download_is_not_a_filesystem_path(self):
        response = await self.client.get("/api/v1/templates/unknown/download")
        self.assertEqual(response.status_code, 404)

"""Public reference downloads only; no database, AI or email is touched."""
import unittest
from hashlib import sha256
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
        self.assertEqual(len(catalog), 8)
        for item in catalog:
            download = await self.client.get(item["download_url"])
            self.assertEqual(download.status_code, 200, item["name"])
            self.assertIn("attachment", download.headers["content-disposition"])
            if item["name"].endswith(".png"):
                self.assertEqual(download.headers["content-type"], "image/png")
                self.assertTrue(download.content.startswith(b'\x89PNG\r\n\x1a\n'))
            elif item["name"].endswith(".pdf"):
                self.assertEqual(download.headers["content-type"], "application/pdf")
                reader = PdfReader(BytesIO(download.content))
                self.assertEqual(len(reader.pages), 1)
                self.assertIn("虚构", reader.pages[0].extract_text())
            else:
                self.assertIn("wordprocessingml", download.headers["content-type"])
                with ZipFile(BytesIO(download.content)) as doc:
                    self.assertIn("word/document.xml", doc.namelist())
                    if item["kind"] == "example" and item["id"] != "meiyu_application_example":
                        self.assertIn("请勿原样提交", doc.read("word/document.xml").decode())

    async def test_yueyuan_bundle_contains_exactly_three_original_templates(self):
        catalog = (await self.client.get("/api/v1/templates")).json()
        originals = [item for item in catalog if item["application_type"] == "yueyuan_third_floor" and item["kind"] == "template"]
        self.assertEqual(len(originals), 3)
        response = await self.client.get("/api/v1/templates/bundles/yueyuan/download")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn("attachment", response.headers["content-disposition"])
        with ZipFile(BytesIO(response.content)) as bundle:
            self.assertCountEqual(bundle.namelist(), [item["name"] for item in originals])
            for item in originals:
                original = await self.client.get(item["download_url"])
                self.assertEqual(bundle.read(item["name"]), original.content)
        self.assertEqual((await self.client.get("/api/v1/templates/bundles/unknown/download")).status_code, 404)

    async def test_supplied_examples_are_preserved_and_keys_have_one_image_only(self):
        catalog = (await self.client.get("/api/v1/templates")).json()
        venue_example = next(item for item in catalog if item["id"] == "meiyu_application_example")
        self.assertEqual(venue_example["name"], "填写示例.docx")
        key_items = [item for item in catalog if item["application_type"] == "key_borrow"]
        self.assertEqual([item["id"] for item in key_items], ["key_borrow_example"])
        self.assertIn("OCR", key_items[0]["description"])
        for example_id, digest in {
            "meiyu_application_example": "2ac630257c621e1190f6cba935dfab9f53011c1340ffe65c836503cf9b841c8f",
            "key_borrow_example": "52fa2e06a8abaeffae0f38f2dbcec6e2f304673c10e456fc172969a039204261",
        }.items():
            download = await self.client.get(f"/api/v1/templates/{example_id}/download")
            self.assertEqual(sha256(download.content).hexdigest(), digest)
        self.assertEqual((await self.client.get("/api/v1/templates/key_borrow_editable_example/download")).status_code, 404)

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

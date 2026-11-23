"""V6 screenshot source selection and privacy: no fabricated project covers."""
import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from live_project_cards_v6 import OWNER, PROJECTS, STANDARD_PATHS, blob_sha, locate

class V6ProjectImageTests(unittest.TestCase):
    def base(self, repo):
        return {
            "private": False, "name": repo, "owner": {"login": OWNER},
            "default_branch": "main", "stargazers_count": 4, "forks_count": 2
        }
    def test_unpublished_project_image_is_a_real_placeholder(self):
        name = PROJECTS[2][1]
        def fetch(url):
            if url.endswith("/"+name):
                return self.base(name)
            raise HTTPError(url,404,"Not Found",{},None)
        metadata, photo = locate(name, fetch)
        self.assertIsNone(metadata["path"])
        self.assertIsNone(metadata["source_sha"])
        self.assertIsNone(photo)
        self.assertEqual(metadata["stars"],4)
    def test_image_appears_after_public_project_upload(self):
        name = PROJECTS[1][1]
        payload=b"\x89PNG\r\n\x1a\n"+b"sample-payload"
        sha=blob_sha(payload)
        cover="assets/profile-cover.png"
        def fetch(url):
            if url.endswith("/"+name): return self.base(name)
            if "/contents/"+cover+"?" in url:
                return {"type":"file","path":cover,"encoding":"base64",
                        "size":len(payload),"sha":sha,
                        "content":base64.b64encode(payload).decode("ascii")}
            raise HTTPError(url,404,"Not Found",{},None)
        metadata,photo=locate(name,fetch)
        self.assertEqual(metadata["path"],cover)
        self.assertEqual(metadata["source_sha"],sha)
        self.assertEqual(photo,payload)
    def test_bad_git_sha_fails_closed(self):
        name = PROJECTS[0][1]
        def fetch(url):
            if url.endswith("/"+name): return self.base(name)
            return {"type":"file","path":STANDARD_PATHS[0],"encoding":"base64",
                    "size":4,"sha":"0"*40,"content":base64.b64encode(b"test").decode()}
        with self.assertRaises(ValueError):
            locate(name,fetch)
    def test_private_repo_metadata_never_processed(self):
        name=PROJECTS[0][1]
        def fetch(url):
            info=self.base(name)
            info["private"]=True
            return info
        with self.assertRaises(ValueError):
            locate(name,fetch)
    def test_end_to_end_raster_cards_and_placeholder(self):
        from PIL import Image
        import io
        import tempfile
        from live_project_cards_v6 import build, verify, CARD_FILES
        stream = io.BytesIO()
        Image.new("RGB", (320, 160), "#28395e").save(stream, "PNG")
        screenshot = stream.getvalue()
        image_sha = blob_sha(screenshot)
        def fetch(url):
            for project in PROJECTS:
                if url.endswith("/" + project[1]):
                    return self.base(project[1])
            if "/morocco2030/contents/assets/profile-cover.png?" in url:
                return {"type":"file","path":"assets/profile-cover.png",
                        "encoding":"base64","size":len(screenshot),"sha":image_sha,
                        "content":base64.b64encode(screenshot).decode("ascii")}
            raise HTTPError(url,404,"Not Found",{},None)
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            result=build(folder,fetch)
            self.assertEqual(len(result["cards"]),3)
            self.assertIsNotNone(result["cards"][0]["path"])
            self.assertIsNone(result["cards"][1]["path"])
            self.assertIsNone(result["cards"][2]["path"])
            self.assertEqual(set(CARD_FILES),{x["file"] for x in result["cards"]})
            self.assertEqual(verify(folder),result)
            for name in CARD_FILES:
                with Image.open(folder/name) as image:
                    self.assertEqual(image.size,(640,560))
                    image.verify()
            (folder/CARD_FILES[0]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"tampered"):
                verify(folder)

    def test_only_allowlisted_public_file_paths(self):
        self.assertNotIn(".env", " ".join(STANDARD_PATHS))
        self.assertTrue(all("profile-" in p or "readme/" in p or "screenshots/" in p for p in STANDARD_PATHS))
if __name__ == "__main__":
    unittest.main()

"""S9 负载：读为主，含 translated fetch。"""
from __future__ import annotations

from locust import HttpUser, between, task


class BrowseUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def public_user(self) -> None:
        self.client.get("/api/v1/users/user0001")

    @task(5)
    def list_buckets(self) -> None:
        self.client.get("/api/v1/users/user0001/buckets")

    @task(4)
    def get_bucket(self) -> None:
        self.client.get("/api/v1/users/user0001/buckets/tools")

    @task(4)
    def list_assets(self) -> None:
        self.client.get("/api/v1/users/user0001/buckets/tools/assets")

    @task(3)
    def raw_asset(self) -> None:
        listing = self.client.get(
            "/api/v1/users/user0001/buckets/tools/assets"
        )
        if listing.status_code != 200:
            return
        items = listing.json().get("items") or []
        if not items:
            return
        asset_id = items[0]["id"]
        self.client.get(
            f"/api/v1/users/user0001/buckets/tools/assets/{asset_id}/raw"
        )

    @task(3)
    def translated(self) -> None:
        self.client.get(
            "/api/v1/users/user0001/buckets/tools/translated",
            params={"target": "codex"},
        )

    @task(1)
    def matrix(self) -> None:
        self.client.get("/api/v1/translation-matrix")

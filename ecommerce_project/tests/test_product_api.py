import pytest
from httpx import AsyncClient, ASGITransport

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
transport = ASGITransport(app=app)
@pytest.mark.asyncio
async def test_get_product():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/product/products/5")
    assert response.status_code == 200 or response.status_code == 404  # handle not found case

@pytest.mark.asyncio
async def test_create_product():
    payload = {
        "product_name": "Test Product",
        "price": 100.0,
        "discount": 10.0,
        "stock": 50,
        "brand": "Test Brand",
        "category_id": 1,
        "description": "This is a test product.",
        "color": "Black",
        "shipping_time": "3-5 days",
        "images": ["img1.jpg", "img2.jpg"]
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/product/products", json=payload)
    assert response.status_code == 201 or response.status_code == 200

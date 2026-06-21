import pytest
import io

@pytest.mark.asyncio
async def test_upload_list_and_delete_document(authenticated_client):
    # 1. Create a dummy CSV file content
    csv_content = "title,description\nMachine Learning,Study of algorithms that learn\nDeep Learning,Neural networks base"
    file_bytes = csv_content.encode("utf-8")
    
    # 2. Upload file
    files = {"file": ("test_ml.csv", io.BytesIO(file_bytes), "text/csv")}
    upload_response = await authenticated_client.post("/api/documents/upload", files=files)
    assert upload_response.status_code == 201
    upload_data = upload_response.json()
    assert "document" in upload_data
    doc_id = upload_data["document"]["id"]
    assert upload_data["document"]["original_filename"] == "test_ml.csv"
    assert upload_data["document"]["file_type"] == "csv"
    assert upload_data["document"]["chunk_count"] > 0
    
    # 3. List documents
    list_response = await authenticated_client.get("/api/documents")
    assert list_response.status_code == 200
    docs = list_response.json()
    assert len(docs) >= 1
    assert any(d["id"] == doc_id for d in docs)
    
    # 4. Get specific document details
    details_response = await authenticated_client.get(f"/api/documents/{doc_id}")
    assert details_response.status_code == 200
    details = details_response.json()
    assert details["original_filename"] == "test_ml.csv"
    
    # 5. Rename document
    rename_response = await authenticated_client.put(f"/api/documents/{doc_id}?new_name=renamed_ml.csv")
    assert rename_response.status_code == 200
    
    # Verify renaming worked
    details_response = await authenticated_client.get(f"/api/documents/{doc_id}")
    assert details_response.status_code == 200
    assert details_response.json()["original_filename"] == "renamed_ml.csv"

    # 6. Delete document
    delete_response = await authenticated_client.delete(f"/api/documents/{doc_id}")
    assert delete_response.status_code == 200
    
    # Verify document is gone
    details_response = await authenticated_client.get(f"/api/documents/{doc_id}")
    assert details_response.status_code == 404

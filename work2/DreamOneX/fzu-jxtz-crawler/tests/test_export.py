"""
Tests for CSV export functionality.
"""
from datetime import datetime
from pathlib import Path
import tempfile

import pandas as pd

from fzu_jxtz_crawler import entries_to_dataframe, export_to_csv
from fzu_jxtz_crawler import AnnouncementEntry, Attachment


class TestEntriesToDataFrame:
    """Tests for entries_to_dataframe function."""
    
    def test_basic_conversion(self):
        """Test basic conversion of entries to DataFrame."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title="Test Announcement 1",
                issuer="Test Department",
                pub_date=datetime(2025, 12, 1),
                body="This is the body",
                attachments=None
            ),
            AnnouncementEntry(
                announcement_id="0002",
                url="https://example.com/2",
                title="Test Announcement 2",
                issuer="Another Department",
                pub_date=datetime(2025, 12, 2),
                body=None,
                attachments=None
            )
        ]
        
        df = entries_to_dataframe(entries, clean_text_fields=False)
        
        assert len(df) == 2
        assert list(df.columns) == [
            "id", "url", "title", "issuer", "pub_date", 
            "body", "attachment_count", "attachment_id", "attachment_name", 
            "attachment_download_times", "attachment_url",
            "attachment_file_code", "attachment_owner"
        ]
        assert df.iloc[0]["id"] == "0001"
        assert df.iloc[0]["url"] == "https://example.com/1"
        assert df.iloc[0]["title"] == "Test Announcement 1"
        assert df.iloc[0]["pub_date"] == "2025-12-01"
        assert df.iloc[0]["body"] == "This is the body"
        assert df.iloc[0]["attachment_count"] == 0
        assert df.iloc[1]["body"] == ""
    
    def test_with_attachments(self):
        """Test conversion with attachments."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title="Test",
                issuer="Dept",
                pub_date=datetime(2025, 12, 1),
                body="Body",
                attachments=[
                    Attachment(
                        attachment_id="000000000123000000000456",
                        name="file1.pdf",
                        download_times=10,
                        url="https://example.com/file1.pdf",
                        owner_code="123",
                        file_code="456",
                        local_path=None
                    ),
                    Attachment(
                        attachment_id="000000000123000000000789",
                        name="file2.xlsx",
                        download_times=5,
                        url="https://example.com/file2.xlsx",
                        owner_code="123",
                        file_code="789",
                        local_path=None
                    )
                ]
            )
        ]
        
        df = entries_to_dataframe(entries, clean_text_fields=False)
        
        # New behavior: one row per attachment
        assert len(df) == 2
        
        row1 = df.iloc[0]
        assert row1["id"] == "0001"
        assert row1["attachment_count"] == 2
        assert row1["attachment_name"] == "file1.pdf"
        assert row1["attachment_url"] == "https://example.com/file1.pdf"
        assert row1["attachment_download_times"] == 10
        
        row2 = df.iloc[1]
        assert row2["id"] == "0001"
        assert row2["attachment_count"] == 2
        assert row2["attachment_name"] == "file2.xlsx"
        assert row2["attachment_url"] == "https://example.com/file2.xlsx"
        assert row2["attachment_download_times"] == 5
    
    def test_text_cleaning(self):
        """Test text cleaning integration."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title="  Test   Title\r\n  ",
                issuer="  Dept  ",
                pub_date=datetime(2025, 12, 1),
                body="Line 1\r\nLine 2  \r\n\r\n\r\nLine 3",
                attachments=None
            )
        ]
        
        df = entries_to_dataframe(entries, clean_text_fields=True)
        
        assert df.iloc[0]["title"] == "Test Title"
        assert df.iloc[0]["issuer"] == "Dept"
        assert df.iloc[0]["body"] == "Line 1\nLine 2\n\nLine 3"
    
    def test_empty_list(self):
        """Test with empty entry list."""
        df = entries_to_dataframe([], clean_text_fields=False)
        
        assert len(df) == 0
        # Empty DataFrame from empty list won't have columns
        # This is expected pandas behavior


class TestExportToCSV:
    """Tests for export_to_csv function."""
    
    def test_basic_export(self):
        """Test basic CSV export."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title="Test Announcement",
                issuer="Test Department",
                pub_date=datetime(2025, 12, 1),
                body="This is the body",
                attachments=None
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            export_to_csv(entries, temp_path, clean_text_fields=False)
            
            # Read back and verify
            df = pd.read_csv(temp_path)
            assert len(df) == 1
            assert df.iloc[0]["id"] == 1  # pandas might read "0001" as 1 if interpreted as int
            assert df.iloc[0]["title"] == "Test Announcement"
            assert df.iloc[0]["url"] == "https://example.com/1"
            
            # Verify file uses LF line endings
            with open(temp_path, 'rb') as f:
                content = f.read()
                assert b'\r\n' not in content  # No CRLF
                assert b'\n' in content  # Has LF
        finally:
            Path(temp_path).unlink()
    
    def test_export_with_text_cleaning(self):
        """Test CSV export with text cleaning."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title="  Test\r\n  Title  ",
                issuer="Dept",
                pub_date=datetime(2025, 12, 1),
                body="Line 1\r\nLine 2",
                attachments=None
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            export_to_csv(entries, temp_path, clean_text_fields=True)
            
            df = pd.read_csv(temp_path)
            # Note: clean_text preserves newlines, which is correct behavior
            # The title "  Test\r\n  Title  " becomes "Test\nTitle" after cleaning
            assert df.iloc[0]["title"] == "Test\nTitle"
            assert df.iloc[0]["body"] == "Line 1\nLine 2"
        finally:
            Path(temp_path).unlink()
    
    def test_export_with_special_characters(self):
        """Test CSV export handles special characters correctly."""
        entries = [
            AnnouncementEntry(
                announcement_id="0001",
                url="https://example.com/1",
                title='Title with "quotes" and, commas',
                issuer="Dept",
                pub_date=datetime(2025, 12, 1),
                body="Body with\nnewlines",
                attachments=None
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            export_to_csv(entries, temp_path, clean_text_fields=False)
            
            # Read back and verify pandas handles escaping
            df = pd.read_csv(temp_path)
            assert df.iloc[0]["title"] == 'Title with "quotes" and, commas'
            assert df.iloc[0]["body"] == "Body with\nnewlines"
        finally:
            Path(temp_path).unlink()

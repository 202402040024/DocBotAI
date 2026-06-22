import os
import re
from typing import Any, Dict, List
import pdfplumber
import docx
import pandas as pd
import xml.etree.ElementTree as ET

class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        # Find separator
        separator = separators[-1]
        new_separators = []
        for i, s in enumerate(separators):
            if s == "":
                separator = s
                new_separators = separators[i+1:]
                break
            if s in text:
                separator = s
                new_separators = separators[i+1:]
                break

        # Split on separator
        if separator != "":
            splits = text.split(separator)
        else:
            splits = list(text)

        # Merge splits into overlapping chunks
        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_len = len(split)
            # If a single split is larger than chunk_size, recursively split it
            if split_len > self.chunk_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split this giant block with smaller separators
                sub_chunks = self._split_text(split, new_separators)
                chunks.extend(sub_chunks)
                continue

            # If adding this split exceeds chunk_size
            if current_length + split_len + (len(separator) if current_chunk else 0) > self.chunk_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                
                # Rollback/Overlap setup
                # Retain items from current_chunk that fit within overlap limit
                overlap_chunk = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    item_len = len(item)
                    if overlap_len + item_len + (len(separator) if overlap_chunk else 0) <= self.chunk_overlap:
                        overlap_chunk.insert(0, item)
                        overlap_len += item_len + (len(separator) if len(overlap_chunk) > 1 else 0)
                    else:
                        break
                current_chunk = overlap_chunk
                current_length = overlap_len

            current_chunk.append(split)
            current_length += split_len + (len(separator) if len(current_chunk) > 1 else 0)

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return [c.strip() for c in chunks if c.strip()]


class DocumentProcessor:
    @staticmethod
    def clean_text(text: str) -> str:
        # Normalize whitespace and strip special control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    def extract_text(cls, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """
        Extracts text from file.
        Returns: List of dicts, each with keys: 'text', 'page_number', 'paragraph_number'
        """
        file_type = file_type.lower()
        if file_type == "pdf":
            return cls._extract_pdf(file_path)
        elif file_type == "docx":
            return cls._extract_docx(file_path)
        elif file_type == "csv":
            return cls._extract_csv(file_path)
        elif file_type == "xml":
            return cls._extract_xml(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @classmethod
    def _extract_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        blocks = []
        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                cleaned = cls.clean_text(text)
                if cleaned:
                    blocks.append({
                        "text": cleaned,
                        "page_number": idx + 1,
                        "paragraph_number": 1
                    })
        return blocks

    @classmethod
    def _extract_docx(cls, file_path: str) -> List[Dict[str, Any]]:
        doc = docx.Document(file_path)
        blocks = []
        para_idx = 1
        for para in doc.paragraphs:
            cleaned = cls.clean_text(para.text)
            if cleaned:
                blocks.append({
                    "text": cleaned,
                    "page_number": 1,
                    "paragraph_number": para_idx
                })
                para_idx += 1
        return blocks

    @classmethod
    def _extract_csv(cls, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_csv(file_path)
        blocks = []
        for idx, row in df.iterrows():
            row_items = []
            for col, val in row.items():
                if pd.notna(val):
                    row_items.append(f"{col}: {val}")
            row_text = ", ".join(row_items)
            cleaned = cls.clean_text(row_text)
            if cleaned:
                blocks.append({
                    "text": cleaned,
                    "page_number": 1,
                    "paragraph_number": idx + 1
                })
        return blocks

    @classmethod
    def _extract_xml(cls, file_path: str) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()
        blocks = []
        
        def parse_element(elem, path="") -> List[str]:
            current_path = f"{path}/{elem.tag}" if path else elem.tag
            results = []
            if elem.text and elem.text.strip():
                results.append(f"{current_path}: {elem.text.strip()}")
            for child in elem:
                results.extend(parse_element(child, current_path))
            return results

        elements = parse_element(root)
        for idx, elem_str in enumerate(elements):
            cleaned = cls.clean_text(elem_str)
            if cleaned:
                blocks.append({
                    "text": cleaned,
                    "page_number": 1,
                    "paragraph_number": idx + 1
                })
        return blocks

    @classmethod
    def process_document(cls, file_path: str, file_type: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Extracts content from a file and chunks it.
        Returns: List of dicts, each with keys: 'chunk_text', 'page_number', 'paragraph_number'
        """
        raw_blocks = cls.extract_text(file_path, file_type)
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        chunked_results = []
        for block in raw_blocks:
            chunks = splitter.split_text(block["text"])
            for idx, chunk in enumerate(chunks):
                chunked_results.append({
                    "chunk_text": chunk,
                    "page_number": block["page_number"],
                    "paragraph_number": block["paragraph_number"] + idx
                })
        return chunked_results

# src/core/gita_chunker.py
from langchain.text_splitter import MarkdownHeaderTextSplitter
from pathlib import Path
import json
import os
from typing import List, Dict
from datetime import datetime
import re

class DocumentChunker:
    def __init__(self):
        
        self.headers_to_split_on = [
            ("### **CHAPTER", "chapter"),   
            ("### **PREFACE**", "preface"), 
            ("### ", "section"),            
            ("## ", "subsection"),         
            ("# ", "title"),               
        ]
        
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            return_each_line=False
        )
        
        self.speakers = ["Dhritirashtra:", "Sanjaya:", "Arjuna:", "Krishna:"]
        
        
        self.metadata = {
            "last_processed": "2025-01-14 13:11:26",
            "processed_by": "ravi-hisoka",
            "version": "1.0",
            "source": "The Bhagavad-Gita (Project Gutenberg)",
            "translator": "Sir Edwin Arnold"
        }

    def _extract_speaker(self, text: str) -> str:
        
        for speaker in self.speakers:
            if speaker in text:
                return speaker.rstrip(':')
        return "Unknown"

    def _clean_text(self, text: str) -> str:
        
        text = re.sub(r'\[FN#\d+\]', '', text)
        
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_chapter_number(self, text: str) -> int:
        
        match = re.search(r'CHAPTER\s+([IVX]+)', text, re.IGNORECASE)
        if match:
            roman_numeral = match.group(1)
            roman_values = {'I': 1, 'V': 5, 'X': 10}
            integer_value = 0
            for i in range(len(roman_numeral)):
                if i > 0 and roman_values[roman_numeral[i]] > roman_values[roman_numeral[i-1]]:
                    integer_value += roman_values[roman_numeral[i]] - 2 * roman_values[roman_numeral[i-1]]
                else:
                    integer_value += roman_values[roman_numeral[i]]
            return integer_value
        return 0

    def _preprocess_content(self, content: str) -> str:
        
        content = re.sub(r'(\n#+[^#\n]+)', r'\n\1', content)
        
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content

    def process_documentation(self, input_path: str) -> List[Dict[str, str]]:
        
        try:
            
            with open(input_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            
            content = self._preprocess_content(content)
            
            
            splits = self.header_splitter.split_text(content)
            
            processed_chunks = []
            current_chapter = 0
            verse_counter = 0
            
            print(f"Initial number of splits: {len(splits)}")  
            
            for split in splits:
                text_content = split.page_content
                headers = split.metadata
                
                print(f"Processing headers: {headers}")  
                
                
                if not text_content.strip():
                    continue
                
                
                if 'chapter' in headers:
                    current_chapter = self._get_chapter_number(headers['chapter'])
                    chunk_type = "chapter"
                elif 'preface' in headers:
                    chunk_type = "preface"
                elif 'section' in headers:
                    chunk_type = "section"
                elif 'title' in headers:
                    chunk_type = "title"
                else:
                    chunk_type = "content"

                
                if chunk_type == "chapter":
                    
                    header_chunk = {
                        "id": f"ch{current_chapter}_header",
                        "type": "chapter_header",
                        "content": headers.get('chapter', ''),
                        "metadata": {
                            "chapter_number": current_chapter,
                            "section_type": "chapter_header",
                            "headers": dict(headers)
                        }
                    }
                    processed_chunks.append(header_chunk)
                    
                    
                    verses = re.split(r'\n\s*\n', text_content)
                    verse_counter = 0
                    
                    for verse in verses:
                        if not verse.strip():
                            continue
                            
                        verse_counter += 1
                        speaker = self._extract_speaker(verse)
                        
                        verse_chunk = {
                            "id": f"ch{current_chapter}_v{verse_counter}",
                            "type": "verse",
                            "content": self._clean_text(verse),
                            "metadata": {
                                "chapter_number": current_chapter,
                                "verse_number": verse_counter,
                                "speaker": speaker,
                                "section_type": "verse",
                                "headers": dict(headers)
                            }
                        }
                        processed_chunks.append(verse_chunk)
                
                else:
                    
                    chunk = {
                        "id": f"{chunk_type}_{len(processed_chunks)}",
                        "type": chunk_type,
                        "content": self._clean_text(text_content),
                        "metadata": {
                            "section_type": chunk_type,
                            "headers": dict(headers)
                        }
                    }
                    processed_chunks.append(chunk)

            print(f"Total chunks processed: {len(processed_chunks)}")  # Debug info
            
            
            self._save_chunks(processed_chunks)
            return processed_chunks

        except Exception as e:
            print(f"Error processing documentation: {str(e)}")
            raise

    def _save_chunks(self, chunks: List[Dict[str, str]]) -> None:
        
        output_dir = Path('data/processed/chunks')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        complete_output = {
            "metadata": self.metadata,
            "chunks": chunks
        }
        
        complete_path = output_dir / f'gita_processed_{timestamp}.json'
        with open(complete_path, 'w', encoding='utf-8') as f:
            json.dump(complete_output, f, indent=2, ensure_ascii=False)


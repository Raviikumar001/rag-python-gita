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
        # Refined header structure to match the document
        self.headers_to_split_on = [
            ("### **CHAPTER", "chapter"),   # Matches chapter headers
            ("### **PREFACE**", "preface"), # Matches preface specifically
            ("### ", "section"),            # Other section headers
            ("## ", "subsection"),          # Subsections
            ("# ", "title"),                # Main titles
        ]
        
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            return_each_line=False
        )
        
        self.speakers = ["Dhritirashtra:", "Sanjaya:", "Arjuna:", "Krishna:"]
        
        # Updated with current time and user
        self.metadata = {
            "last_processed": "2025-01-14 13:11:26",
            "processed_by": "ravi-hisoka",
            "version": "1.0",
            "source": "The Bhagavad-Gita (Project Gutenberg)",
            "translator": "Sir Edwin Arnold"
        }

    def _extract_speaker(self, text: str) -> str:
        """Extract speaker name from text."""
        for speaker in self.speakers:
            if speaker in text:
                return speaker.rstrip(':')
        return "Unknown"

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove footnotes
        text = re.sub(r'\[FN#\d+\]', '', text)
        # Remove multiple spaces and normalize newlines
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_chapter_number(self, text: str) -> int:
        """Extract chapter number from text."""
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
        """Preprocess the content to ensure proper markdown formatting."""
        # Ensure proper spacing around headers
        content = re.sub(r'(\n#+[^#\n]+)', r'\n\1', content)
        # Remove multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content

    def process_documentation(self, input_path: str) -> List[Dict[str, str]]:
        """Process the Gita markdown file."""
        try:
            # Read and preprocess the markdown file
            with open(input_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Preprocess content
            content = self._preprocess_content(content)
            
            # Split the document using langchain's splitter
            splits = self.header_splitter.split_text(content)
            
            processed_chunks = []
            current_chapter = 0
            verse_counter = 0
            
            print(f"Initial number of splits: {len(splits)}")  # Debug info
            
            for split in splits:
                text_content = split.page_content
                headers = split.metadata
                
                print(f"Processing headers: {headers}")  # Debug info
                
                # Skip empty content
                if not text_content.strip():
                    continue
                
                # Process based on header type
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

                # Split content into smaller chunks if it's a chapter
                if chunk_type == "chapter":
                    # First create chapter header chunk
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
                    
                    # Then process verses
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
                    # Process non-chapter content
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
            
            # Save the processed chunks
            self._save_chunks(processed_chunks)
            return processed_chunks

        except Exception as e:
            print(f"Error processing documentation: {str(e)}")
            raise

    def _save_chunks(self, chunks: List[Dict[str, str]]) -> None:
        """Save processed chunks to files."""
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

# # src/core/chunker.py

# from langchain.text_splitter import MarkdownHeaderTextSplitter
# from pathlib import Path
# import json
# import os
# from typing import List, Dict
# from datetime import datetime
# import re

# class DocumentChunker:
#     def __init__(self):
        
#         self.headers_to_split_on = [
#             ("## ", "h2"),   
#             ("### ", "h3"),  
#         ]
        
#         self.header_splitter = MarkdownHeaderTextSplitter(
#             headers_to_split_on=self.headers_to_split_on,
#             return_each_line=False
#         )

#     def is_api_section(self, content: str) -> bool:
        
#         return any(marker in content for marker in [
#             "API",
#             "Request",
#             "Response",
#             "Parameters",
#             "curl",
#             "HTTP"
#         ])

#     def process_documentation(self, input_path: str) -> List[Dict[str, str]]:
#         try:
            
#             with open(input_path, 'r', encoding='utf-8') as file:
#                 content = file.read()

            
#             sections = re.split(r'(?=# )', content)
            
           
#             processed_chunks = []
            
#             for section_idx, section in enumerate(sections):
#                 if not section.strip():
#                     continue

            
#                 if section.startswith('# Introduction') or section.startswith('# Getting Started'):
#                     chunk_data = {
#                         'id': len(processed_chunks),
#                         'content': section.strip(),
#                         'metadata': {
#                             'section': section.split('\n')[0].replace('#', '').strip(),
#                             'type': 'documentation',
#                             'position': len(processed_chunks),
#                             'source': input_path
#                         }
#                     }
#                     processed_chunks.append(chunk_data)
#                     continue

               
#                 api_sections = re.split(r'(?=## )', section)
#                 for api_section in api_sections:
#                     if not api_section.strip():
#                         continue

                  
#                     title_match = re.match(r'##\s+(.+?)(?:\n|$)', api_section)
#                     section_title = title_match.group(1) if title_match else "Untitled Section"

#                     chunk_data = {
#                         'id': len(processed_chunks),
#                         'content': api_section.strip(),
#                         'metadata': {
#                             'section': section_title,
#                             'type': 'api_documentation' if self.is_api_section(api_section) else 'documentation',
#                             'position': len(processed_chunks),
#                             'source': input_path
#                         }
#                     }
#                     processed_chunks.append(chunk_data)

       
#             self._save_chunks(processed_chunks)
#             return processed_chunks

#         except Exception as e:
#             print(f"Error processing documentation: {str(e)}")
#             raise

#     def _save_chunks(self, chunks: List[Dict[str, str]]) -> None:
#         output_dir = Path('data/processed/chunks')
#         output_dir.mkdir(parents=True, exist_ok=True)
        
#         timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
#         output_path = output_dir / f'processed_chunks_{timestamp}.json'
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(chunks, f, indent=2, ensure_ascii=False)
# src/services/gemini.py
import google.generativeai as genai
from typing import List
from src.utils.logger import get_logger
import os

logger = get_logger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        logger.info("Initialized Gemini service")

    def _prepare_prompt(self, question: str, context_chunks: List[str]) -> str:
        context_text = "\n".join(context_chunks)
        
        prompt = f"""You are a knowledgeable assistant for the Bhagavad Gita, focusing on providing 
        clear and insightful explanations of its teachings, verses, and philosophical concepts.

        Context from the Bhagavad Gita:
        ```
        {context_text}
        ```

        Guidelines:
        1. Directly address the user's question about the Gita's teachings.
        2. If the question involves specific verses, cite them and provide their context.
        3. Explain Sanskrit terms when they appear in the text.
        4. Connect verses to their broader philosophical or spiritual context.
        5. If relevant, mention which chapter (and speaker) the teaching comes from.
        6. Provide practical interpretations that relate to modern life.
        7. When appropriate, reference related verses that support or expand the teaching.
        8. Maintain proper formatting for verse citations and Sanskrit terms.
        9. Use markdown for better readability.
       

        Question: {question}

        Provide a clear explanation, citing specific verses where relevant. Include both the literal 
        meaning and the deeper philosophical significance when appropriate."""
        
        return prompt

    def get_answer(self, question: str, context_chunks: List[str]) -> str:
        try:
            prompt = self._prepare_prompt(question, context_chunks)
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            
            # Format the answer with proper markdown
            answer = self._format_response(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise

    def _format_response(self, text: str) -> str:
        
        lines = text.split('\n')
        formatted_lines = []
        in_verse_block = False
        
        for line in lines:
            
            if line.strip().startswith('Chapter') or line.strip().startswith('Verse'):
                if not in_verse_block:
                    formatted_lines.extend(['```verse', line])
                    in_verse_block = True
                else:
                    formatted_lines.append(line)
            # Handle Sanskrit terms
            elif any(sanskrit_marker in line for sanskrit_marker in ['[Sanskrit]', '(Sanskrit)']):
                formatted_lines.append(f"*{line}*")
            
            elif in_verse_block and line.strip() == '':
                formatted_lines.extend(['```', ''])
                in_verse_block = False
            
            else:
                
                for speaker in ['Krishna:', 'Arjuna:', 'Sanjaya:', 'Dhritirashtra:']:
                    if line.strip().startswith(speaker):
                        line = f"**{speaker}** {line[len(speaker):]}"
                formatted_lines.append(line)
        
        
        if in_verse_block:
            formatted_lines.append('```')
            
        return '\n'.join(formatted_lines)

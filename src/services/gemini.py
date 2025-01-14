# src/services/gemini.py

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
        self.model = genai.GenerativeModel('gemini-pro')
        
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
        """Format the response with proper markdown and verse citations."""
        lines = text.split('\n')
        formatted_lines = []
        in_verse_block = False
        
        for line in lines:
            # Handle verse citations
            if line.strip().startswith('Chapter') or line.strip().startswith('Verse'):
                if not in_verse_block:
                    formatted_lines.extend(['```verse', line])
                    in_verse_block = True
                else:
                    formatted_lines.append(line)
            # Handle Sanskrit terms
            elif any(sanskrit_marker in line for sanskrit_marker in ['[Sanskrit]', '(Sanskrit)']):
                formatted_lines.append(f"*{line}*")
            # Handle verse blocks
            elif in_verse_block and line.strip() == '':
                formatted_lines.extend(['```', ''])
                in_verse_block = False
            # Handle regular text
            else:
                # Add emphasis to speaker names
                for speaker in ['Krishna:', 'Arjuna:', 'Sanjaya:', 'Dhritirashtra:']:
                    if line.strip().startswith(speaker):
                        line = f"**{speaker}** {line[len(speaker):]}"
                formatted_lines.append(line)
        
        # Close any open verse block
        if in_verse_block:
            formatted_lines.append('```')
            
        return '\n'.join(formatted_lines)
# import google.generativeai as genai
# from typing import List
# from src.utils.logger import get_logger
# import os

# logger = get_logger(__name__)

# class GeminiService:
#     def __init__(self):
        
#         self.api_key = os.getenv("GEMINI_API_KEY")
#         if not self.api_key:
#             raise ValueError("GEMINI_API_KEY not found in environment variables")
            
#         genai.configure(api_key=self.api_key)
#         self.model = genai.GenerativeModel('gemini-pro')
        
#         logger.info("Initialized Gemini service")

#     def _prepare_prompt(self, question: str, context_chunks: List[str]) -> str:
        
#         context_text = "\n".join(context_chunks)
        
#         prompt = f"""You are a focused API documentation assistant for the Crustdata API. 
#         Your goal is to provide clear and relevant information to help developers 
#         effectively use the API based on their queries.

#         Context from the API documentation:
#         ```
#         {context_text}
#         ```

#         Guidelines:
#         1. Directly answer the user's query, focusing on their specific needs.
#         2. If the question involves specific values (like regions), explicitly mention where to find valid options, such as in tables or linked resources.
#         3. Clearly state the relevant endpoint that can be used to fulfill the request.
#         4. Summarize key values or options from tables that relate to the user's question.
#         5. Provide a complete, working curl example for the API usage.
#         6. Include links to relevant resources or documentation that can assist the user, especially for finding valid filter values.
#         7. If the user is facing common issues (like invalid input), provide solutions or guidance on how to correct them.
#         8. Maintain code formatting in your response.
#         9. Use markdown for better readability.

#         Question: {question}

#         Provide a practical example that developers can use immediately, including all necessary headers, authentication, and request body formatting. If applicable, summarize the purpose of the API call in a single sentence before the curl example."""
        
#         return prompt




#     def get_answer(self, question: str, context_chunks: List[str]) -> str:
        
#         try:
#             prompt = self._prepare_prompt(question, context_chunks)
#             response = self.model.generate_content(prompt)  # Remove await
            
           
#             answer = response.text.strip()
            
            
#             if "```" not in answer:
#                 answer = self._format_code_blocks(answer)
                
#             return answer
            
#         except Exception as e:
#             logger.error(f"Gemini API error: {str(e)}")
#             raise

#     def _format_code_blocks(self, text: str) -> str:
        
#         lines = text.split('\n')
#         formatted_lines = []
#         in_code_block = False
        
#         for line in lines:
#             if line.strip().startswith('curl ') and not in_code_block:
#                 formatted_lines.extend(['```bash', line])
#                 in_code_block = True
#             elif line.strip().startswith('{') and not in_code_block:
#                 formatted_lines.extend(['```json', line])
#                 in_code_block = True
#             elif in_code_block and line.strip() == '':
#                 formatted_lines.extend(['```', ''])
#                 in_code_block = False
#             else:
#                 formatted_lines.append(line)
                
#         if in_code_block:
#             formatted_lines.append('```')
            
#         return '\n'.join(formatted_lines)
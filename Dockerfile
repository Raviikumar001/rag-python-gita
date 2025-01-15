# Dockerfile
FROM python:3.11-slim



COPY requirements.txt .


RUN pip3 install -r requirements.txt


COPY . .


RUN mkdir -p  data/processed/faiss_index data/processed/chunks logs



# Run the application
CMD ["python", "main.py"]
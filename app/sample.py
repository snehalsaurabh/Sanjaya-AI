
# ##############################################################################################

# from fastapi import APIRouter, HTTPException
# from typing import List
# import requests
# import openai
# from app.utils import extract_text_from_file, embed_text, cosine_similarity
# import os
# from dotenv import load_dotenv
# from pydantic import BaseModel
# from langchain_community.embeddings import OpenAIEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain_community.document_loaders import PyPDFLoader, CSVLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# # Load environment variables from .env file
# load_dotenv()

# chat_router = APIRouter()

# # API endpoints for bad words
# GET_BADWORDS_URL = os.getenv("GET_BADWORDS_URL")
# ADD_FLAGGED_WORD_URL = os.getenv("ADD_BADWORD_URL")

# # API endpoints for files
# FETCH_FILES_URL = os.getenv("GET_FILES_URL")

# # OpenAI API key (ensure it's stored in a safe environment)
# openai.api_key = os.getenv("OPENAI_API_KEY")

# vector_store = None

# def fetch_file_content(file_url: str):
#     try:
#         response = requests.get(file_url)
#         response.raise_for_status()  # Raises HTTPError for bad responses
#         return response.content
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch file: {str(e)}")

# ## Function to initialize the vector store
# def initialize_vector_store():
#     global vector_store

#     # Check if vector_store is already initialized
#     if vector_store is not None:
#         return

#     # Fetch files from the external API
#     response = requests.get(FETCH_FILES_URL)
#     if response.status_code != 200:
#         raise HTTPException(status_code=response.status_code, detail="Failed to fetch files.")

#     files = response.json()
#     if not files:
#         raise HTTPException(status_code=404, detail="No files found.")

#     # Get the latest file by ID
#     latest_file = max(files, key=lambda x: x['id'])
#     file_url = latest_file['url']
#     file_type = latest_file['type']

#     # Download the file content
#     file_content = fetch_file_content(file_url)

#     # Process the file based on its type (PDF, CSV)
#     if file_type == "application/pdf":
#         loader = PyPDFLoader(file_content)
#     elif file_type == "text/csv":
#         loader = CSVLoader(file_content)
#     else:
#         raise HTTPException(status_code=400, detail="Unsupported file format.")

#     # Load and split the text
#     documents = loader.load()
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
#     docs = text_splitter.split_documents(documents)

#     # Create embeddings and initialize the vector store
#     embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
#     vector_store = FAISS.from_documents(docs, embeddings)

# def add_s3_pdf_to_vector_store(s3_pdf_url: str):
#     global vector_store

#     # Fetch PDF from S3
#     file_content = fetch_file_content(s3_pdf_url)

#     # Load and process the PDF
#     loader = PyPDFLoader(file_content)
#     documents = loader.load()
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
#     docs = text_splitter.split_documents(documents)

#     # Create embeddings and update the vector store
#     embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
#     if vector_store is None:
#         vector_store = FAISS.from_documents(docs, embeddings)
#     else:
#         new_vector_store = FAISS.from_documents(docs, embeddings)
#         vector_store.add_vector_store(new_vector_store)

# # Get bad words list from API
# def get_bad_words() -> List[str]:
#     response = requests.get(GET_BADWORDS_URL)
#     if response.status_code == 200:
#         badwords_data = response.json()
#         return [word['word'] for word in badwords_data]
#     else:
#         raise HTTPException(status_code=response.status_code, detail="Failed to retrieve bad words.")

# # Add flagged bad word to API
# def flag_bad_word(word: str):
#     payload = {"word": word}
#     response = requests.post(ADD_FLAGGED_WORD_URL, json=payload)
#     if response.status_code != 200:
#         raise HTTPException(status_code=response.status_code, detail="Failed to flag bad word.")

# # Function to check and censor bad words
# def censor_bad_words(user_input: str) -> str:
#     bad_words = get_bad_words()
#     censored_input = user_input
#     flagged_words = []

#     for word in bad_words:
#         if word.lower() in user_input.lower():
#             censored_input = censored_input.replace(word, "***")
#             flagged_words.append(word)

#     # Flag bad words found in the user input
#     for word in flagged_words:
#         flag_bad_word(word)

#     return censored_input

# # Function to interact with OpenAI API
# def get_openai_response(prompt: str) -> str:
#     response = openai.Completion.create(
#         model="gpt-3.5",
#         prompt=prompt,
#         max_tokens=150
#     )
#     return response.choices[0].text.strip()

# # Function to find the best matching document text using vector similarity
# def query_documents(query: str):
#     if not vector_store:
#         raise HTTPException(status_code=404, detail="No documents uploaded for querying.")
    
#     query_embedding = embed_text(query)
#     best_match = None
#     best_score = -1

#     for doc in vector_store:
#         similarity_score = cosine_similarity(query_embedding, doc['embedding'])
#         if similarity_score > best_score:
#             best_score = similarity_score
#             best_match = doc

#     return best_match['text'] if best_match else None

# # Define a request body model
# class ChatRequest(BaseModel):
#     user_input: str

# # Refactor the chat endpoint to ensure vector store is initialized before querying
# @chat_router.post("/chat")
# async def chat_with_bot(request: ChatRequest):
#     user_input = request.user_input
#     global vector_store
#     try:
#         # Censor bad words and flag them
#         censored_input = censor_bad_words(user_input)

#         # Initialize vector store if needed
#         if vector_store is None:
#             initialize_vector_store()

#         # Add S3 PDF to vector store
#         s3_pdf_url = "https://sih2024.s3.ap-southeast-2.amazonaws.com/Indian+Labour+Laws.pdf"
#         add_s3_pdf_to_vector_store(s3_pdf_url)

#         # Query documents and get response
#         document_response = query_documents(censored_input)
#         prompt = f"User query: {censored_input}. Relevant document content: {document_response if document_response else 'No document found.'}. Provide an answer based on this information."
#         openai_response = get_openai_response(prompt)

#         # Get documents from vector store
#         docs = vector_store.similarity_search(censored_input, k=5)
#         context = "\n".join([doc.page_content for doc in docs])
#         response = openai.Completion.create(
#             engine="gpt-3.5",
#             prompt=f"Context: {context}\n\nUser Query: {censored_input}\n\nProvide a detailed response:",
#             max_tokens=300,
#             temperature=0.5,
#         )

#         answer = response.choices[0].text.strip()
#         return {"response": openai_response, "flagged": censored_input != user_input, "document_answer": answer}

#     except Exception as e:
#         # Log error details for debugging
#         print(f"Error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
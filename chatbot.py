"""
RAG Chatbot for University of the Cumberlands
Streamlit interface with Bedrock Claude + ChromaDB retrieval.
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv
import boto3
import chromadb

load_dotenv()

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "ucumberlands"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024
LLM_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
TOP_K = 10
RELEVANCE_THRESHOLD = 0.3


@st.cache_resource
def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


@st.cache_resource
def get_chroma_collection():
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_collection(name=COLLECTION_NAME)


def get_query_embedding(client, query):
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL,
        body=json.dumps({"inputText": query, "dimensions": EMBEDDING_DIMENSIONS}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def retrieve_context(collection, bedrock_client, query, top_k=TOP_K):
    query_embedding = get_query_embedding(bedrock_client, query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = 1 - distance  # ChromaDB cosine distance → similarity
            chunks.append({
                "text": doc,
                "metadata": meta,
                "similarity": similarity,
            })

    return chunks


def build_context_block(chunks):
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source_info = f"[Source {i}: {meta.get('title', 'Unknown')} | {meta.get('section', '')} | {meta.get('url', '')}]"
        context_parts.append(f"{source_info}\n{chunk['text']}")
    return "\n\n---\n\n".join(context_parts)


def generate_response(bedrock_client, query, context_block, chat_history):
    system_prompt = """You are a helpful assistant for the University of the Cumberlands. You answer questions from students, prospective students, parents, and staff based ONLY on the provided context from the university website.

RULES:
1. Only answer based on the provided context. Do not use knowledge outside the context.
2. Cite your sources for every factual claim using the format: [Source: page title](URL)
3. If the context does not contain enough information to answer the question, say: "I don't have enough information from the University of the Cumberlands website to answer this question. Please contact the relevant department or visit ucumberlands.edu for more details."
4. Be helpful, concise, and accurate.
5. For contact information, provide the exact details from the context (phone, email, location).
6. If the question is clearly unrelated to the university, politely redirect: "I'm designed to help with questions about the University of the Cumberlands. Could you ask something related to the university?"
"""

    messages = []
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_message = f"""Based on the following context from the University of the Cumberlands website, answer the user's question.

CONTEXT:
{context_block}

USER QUESTION: {query}

Provide a helpful, accurate answer with source citations."""

    messages.append({"role": "user", "content": user_message})

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": messages,
    })

    response = bedrock_client.invoke_model(modelId=LLM_MODEL, body=body)
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def main():
    st.set_page_config(
        page_title="UC Cumberlands Assistant",
        page_icon="🎓",
        layout="wide",
    )

    st.title("🎓 University of the Cumberlands Assistant")
    st.caption("Ask me anything about UC — admissions, programs, student life, tuition, and more.")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "sources" not in st.session_state:
        st.session_state.sources = []

    # Sidebar with sources
    with st.sidebar:
        st.header("📚 Sources")
        if st.session_state.sources:
            for source in st.session_state.sources:
                with st.expander(f"📄 {source['title'][:50]}..."):
                    st.write(f"**Section:** {source.get('section', 'N/A')}")
                    st.write(f"**Category:** {source.get('category', 'N/A')}")
                    st.write(f"**Relevance:** {source.get('similarity', 0):.0%}")
                    st.write(f"[🔗 Visit Page]({source.get('url', '#')})")
        else:
            st.info("Sources will appear here after you ask a question.")

        st.divider()
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.sources = []
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about UC Cumberlands..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching university resources..."):
                try:
                    bedrock_client = get_bedrock_client()
                    collection = get_chroma_collection()

                    # Retrieve relevant chunks
                    chunks = retrieve_context(collection, bedrock_client, prompt)

                    # Check relevance threshold
                    if not chunks or chunks[0]["similarity"] < RELEVANCE_THRESHOLD:
                        response = "I don't have enough information from the University of the Cumberlands website to answer this question. Please contact the relevant department or visit [ucumberlands.edu](https://www.ucumberlands.edu) for more details."
                        st.session_state.sources = []
                    else:
                        # Build context and generate response
                        context_block = build_context_block(chunks[:5])
                        chat_history = st.session_state.messages[:-1]  # Exclude current message
                        response = generate_response(
                            bedrock_client, prompt, context_block, chat_history[-6:]  # Last 3 turns
                        )

                        # Update sources sidebar
                        st.session_state.sources = [
                            {**c["metadata"], "similarity": c["similarity"]}
                            for c in chunks[:5]
                        ]

                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()

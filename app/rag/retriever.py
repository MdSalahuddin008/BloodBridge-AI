from app.rag.vector_store import create_vector_store


vector_store = create_vector_store()


retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)


def refresh_vector_store():
    global vector_store, retriever

    vector_store = create_vector_store()
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 3}
    )


def retrieve_documents(query: str):
    return retriever.invoke(query)
